"""LangGraph StructuredTool bindings for WS3 tau-retail canonical tools."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from adapter.retail_core.env import RetailEnv
from adapter.retail_tool_factory import build_tool_specs


def make_retail_tools(
    env: RetailEnv,
    allowed_tools: list[str] | None = None,
) -> list[StructuredTool]:
    """Register canonical retail tools whose bodies only forward to RetailEnv."""
    tools: list[StructuredTool] = []
    for spec in build_tool_specs(env, allowed_tools):
        tools.append(
            StructuredTool.from_function(
                func=spec["invoke"],
                name=spec["name"],
                description=spec["description"],
                args_schema=spec["args_schema"],
            )
        )
    return tools


def invoke_retail_tool(
    tools: list[StructuredTool],
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Invoke one registered retail tool by name (used by offline wrapper tests)."""
    tool_by_name = {tool.name: tool for tool in tools}
    if name not in tool_by_name:
        raise KeyError(f"tool not registered: {name}")
    return tool_by_name[name].invoke(arguments)
