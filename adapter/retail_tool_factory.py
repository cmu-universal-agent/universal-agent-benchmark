"""Build framework-native retail tools from the WS3 tau-retail contract.

Shared by LangGraph, CrewAI, and OpenAI Agents SDK thin wrappers. Each tool
forwards to ``RetailEnv.call_tool()`` with no business logic.
"""

from __future__ import annotations

import dataclasses
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field, create_model

from adapter.retail_core.env import RetailEnv

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tools" / "tau_retail_contract.json"


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def _load_tool_schema(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def _python_type_for_property(prop_schema: dict[str, Any]) -> type:
    json_type = prop_schema.get("type")
    if json_type == "string":
        return str
    if json_type == "array":
        item_type = prop_schema.get("items", {}).get("type")
        if item_type == "string":
            return list[str]
    return Any


def args_model_from_json_schema(tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Convert a contract input schema into a Pydantic model for tool binding."""
    fields: dict[str, tuple[type, Any]] = {}
    required = set(schema.get("required", []))
    for prop_name, prop_schema in schema.get("properties", {}).items():
        py_type = _python_type_for_property(prop_schema)
        if prop_name in required:
            fields[prop_name] = (py_type, Field(...))
        else:
            fields[prop_name] = (py_type | None, Field(default=None))
    model_name = "".join(part.title() for part in tool_name.split("_")) + "Args"
    return create_model(model_name, **fields)  # type: ignore[call-overload]


def canonical_tool_names() -> list[str]:
    contract = load_contract()
    return [tool["name"] for tool in contract["tools"]]


def make_tool_callable(env: RetailEnv, tool_name: str) -> Callable[..., dict[str, Any]]:
    def _invoke(**arguments: Any) -> dict[str, Any]:
        cleaned = {key: value for key, value in arguments.items() if value is not None}
        result = env.call_tool(tool_name, cleaned)
        return dataclasses.asdict(result)

    return _invoke


def build_tool_specs(
    env: RetailEnv,
    allowed_tools: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return metadata for each canonical tool: name, schema model, invoke callable."""
    contract = load_contract()
    allowed = set(allowed_tools) if allowed_tools is not None else None
    specs: list[dict[str, Any]] = []

    for tool in contract["tools"]:
        name = tool["name"]
        if allowed is not None and name not in allowed:
            continue
        schema = _load_tool_schema(tool["input_schema"])
        specs.append(
            {
                "name": name,
                "description": f"Retail canonical tool: {name}",
                "args_schema": args_model_from_json_schema(name, schema),
                "invoke": make_tool_callable(env, name),
            }
        )
    return specs
