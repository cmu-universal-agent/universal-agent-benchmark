#!/usr/bin/env python3
"""Offline feasibility probe for WS3 LangGraph retail thin wrapper.

Does NOT call an LLM. Validates:
1) dynamic @tool factories bound to a shared RetailEnv-like object
2) ToolNode executes tools and returns dict ToolResult payloads
3) trace/final_state can be collected post-run for wrapper evidence

Run: python3 scripts/feasibility_langgraph_retail_wrapper.py
"""

from __future__ import annotations

import dataclasses
import json
import operator
import sys
import uuid
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field, create_model
from typing_extensions import TypedDict


@dataclasses.dataclass
class ToolResult:
    ok: bool
    data: dict | None = None
    error_type: str | None = None
    error_message: str | None = None
    state_changed: bool = False


class MockRetailEnv:
    """Minimal stand-in for adapter.retail_core.env.RetailEnv."""

    def __init__(self) -> None:
        self.case_id: str | None = None
        self.reset_id: str | None = None
        self.allowed_tools: frozenset[str] = frozenset()
        self._trace: list[dict[str, Any]] = []

    def reset(self, case_id: str, reset_id: str, seed: int | None = None) -> dict:
        self.case_id = case_id
        self.reset_id = reset_id
        self.allowed_tools = frozenset(
            ["get_order_details", "cancel_pending_order", "return_delivered_order_items"]
        )
        self._trace = []
        return {"case": {"case_id": case_id}, "state": {"seed": seed or 42}}

    def call_tool(self, name: str, arguments: dict, *, retry_of: str | None = None) -> ToolResult:
        call_id = f"tc-{uuid.uuid4().hex[:8]}"
        if name not in self.allowed_tools:
            result = ToolResult(
                ok=False,
                error_type="disallowed_tool",
                error_message=f"tool not allowed: {name}",
            )
        elif name == "get_order_details":
            result = ToolResult(ok=True, data={"order_id": arguments["order_id"], "status": "delivered"})
        else:
            result = ToolResult(ok=True, data={"applied": name, **arguments}, state_changed=True)

        self._trace.append(
            {
                "tool_call_id": call_id,
                "tool_name": name,
                "arguments": arguments,
                "retry_of": retry_of,
                "ok": result.ok,
            }
        )
        return result

    def get_trace(self) -> list[dict]:
        return list(self._trace)

    def get_final_state(self) -> dict:
        return {"case_id": self.case_id, "tool_calls": len(self._trace)}


# Minimal contract fragment: real wrapper must load full schemas from
# tools/tau_retail_contract.json + tools/schemas/*.schema.json.
CONTRACT_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_order_details": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
    },
    "cancel_pending_order": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["order_id", "reason"],
    },
}


def _args_model_from_json_schema(tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Build a Pydantic args model so ToolNode receives structured kwargs."""

    fields: dict[str, tuple[type, Any]] = {}
    for prop, spec in schema.get("properties", {}).items():
        py_type = str if spec.get("type") == "string" else Any
        default = ... if prop in schema.get("required", []) else None
        fields[prop] = (py_type, Field(default=default))
    model_name = "".join(part.title() for part in tool_name.split("_")) + "Args"
    return create_model(model_name, **fields)  # type: ignore[call-overload]


def make_retail_tools(env: MockRetailEnv, names: list[str]) -> list[StructuredTool]:
    tools: list[StructuredTool] = []

    for tool_name in names:
        schema = CONTRACT_TOOL_SCHEMAS[tool_name]
        args_model = _args_model_from_json_schema(tool_name, schema)

        def _make_invoke(name: str):
            def _invoke(**arguments: Any) -> dict:
                return dataclasses.asdict(env.call_tool(name, arguments))

            return _invoke

        tools.append(
            StructuredTool.from_function(
                func=_make_invoke(tool_name),
                name=tool_name,
                description=f"Retail canonical tool: {tool_name}",
                args_schema=args_model,
            )
        )
    return tools


class MessagesState(TypedDict):
    messages: Annotated[list, operator.add]


def run_scripted_agent(env: MockRetailEnv, tools: list[StructuredTool]) -> dict:
    """Deterministic graph: one model turn with tool_calls, then ToolNode."""

    tool_node = ToolNode(tools)
    tool_by_name = {t.name: t for t in tools}

    def fake_model(_state: MessagesState):
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_order_details",
                            "args": {"order_id": "O5001"},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        }

    graph = StateGraph(MessagesState)
    graph.add_node("model", fake_model)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "model")
    graph.add_edge("model", "tools")
    graph.add_edge("tools", END)
    compiled = graph.compile()

    out = compiled.invoke({"messages": [HumanMessage(content="handle order O5001")]})
    last_tool = out["messages"][-1]
    assert isinstance(last_tool, ToolMessage)

    content = last_tool.content
    if isinstance(content, str):
        parsed = json.loads(content)
    else:
        parsed = content

    return {
        "tool_message_content": parsed,
        "trace_len": len(env.get_trace()),
        "final_state": env.get_final_state(),
    }


def main() -> int:
    env = MockRetailEnv()
    env.reset("RETAIL-E5-001", reset_id=f"run-{uuid.uuid4().hex}", seed=42)

    names = ["get_order_details", "cancel_pending_order"]
    tools = make_retail_tools(env, names)
    result = run_scripted_agent(env, tools)

    checks = []
    checks.append(("trace_recorded", result["trace_len"] == 1))
    checks.append(("tool_ok", result["tool_message_content"].get("ok") is True))
    checks.append(
        ("order_id_roundtrip", result["tool_message_content"]["data"]["order_id"] == "O5001")
    )
    checks.append(("final_state", result["final_state"]["tool_calls"] == 1))

    print("LangGraph retail wrapper feasibility")
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")

    all_ok = all(ok for _, ok in checks)
    if all_ok:
        print("\nFEASIBILITY_OK: thin-wrapper pattern works offline (no LLM).")
        return 0
    print("\nFEASIBILITY_FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
