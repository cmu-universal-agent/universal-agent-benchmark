"""OpenAI Agents SDK function_tool bindings for WS3 tau-retail canonical tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from adapter.retail_core.env import RetailEnv
from adapter.retail_tool_factory import build_tool_specs


def invoke_retail_tool(
    tools: list[Any],
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Invoke one registered SDK tool by name (used by offline wrapper tests)."""
    from agents.tool_context import ToolContext

    tool_by_name = {tool.name: tool for tool in tools}
    if name not in tool_by_name:
        raise KeyError(f"tool not registered: {name}")
    tool = tool_by_name[name]
    raw_arguments = json.dumps(arguments)
    context = ToolContext(
        context=None,
        tool_name=name,
        tool_call_id=f"offline-{name}",
        tool_arguments=raw_arguments,
    )
    return json.loads(
        asyncio.run(tool.on_invoke_tool(context, raw_arguments))
    )


def make_retail_tools(env: RetailEnv, allowed_tools: list[str] | None = None) -> list[Any]:
    """Register canonical retail tools whose bodies only forward to RetailEnv."""
    from agents import FunctionTool

    tools: list[Any] = []
    for spec in build_tool_specs(env, allowed_tools):
        invoke = spec["invoke"]

        async def on_invoke_tool(
            _context: Any,
            raw_arguments: str,
            *,
            _invoke: Any = invoke,
        ) -> str:
            arguments = json.loads(raw_arguments)
            return json.dumps(_invoke(**arguments), ensure_ascii=False)

        tools.append(
            FunctionTool(
                name=spec["name"],
                description=spec["description"],
                params_json_schema=spec["args_schema"].model_json_schema(),
                on_invoke_tool=on_invoke_tool,
            )
        )
    return tools
