"""OpenAI Agents SDK function_tool bindings for WS3 tau-retail canonical tools."""

from __future__ import annotations

import inspect
import json
from typing import Any

from adapter.retail_core.env import RetailEnv
from adapter.retail_tool_factory import build_tool_specs


def invoke_retail_tool(
    env: RetailEnv,
    name: str,
    arguments: dict[str, Any],
    *,
    allowed_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Invoke one retail tool through the shared factory (offline tests)."""
    for spec in build_tool_specs(env, allowed_tools):
        if spec["name"] == name:
            return spec["invoke"](**arguments)
    raise KeyError(f"tool not registered: {name}")


def _build_tool_function(
    name: str,
    description: str,
    args_schema: type,
    invoke: Any,
) -> Any:
    """Build a typed handler ``function_tool`` can introspect."""

    def handler(**kwargs: Any) -> str:
        return json.dumps(invoke(**kwargs), ensure_ascii=False)

    handler.__name__ = name
    handler.__doc__ = description

    annotations: dict[str, Any] = {"return": str}
    parameters: list[inspect.Parameter] = []
    for field_name, field_info in args_schema.model_fields.items():
        annotations[field_name] = field_info.annotation
        parameters.append(
            inspect.Parameter(
                field_name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=field_info.annotation,
            )
        )
    handler.__annotations__ = annotations
    handler.__signature__ = inspect.Signature(
        parameters=parameters,
        return_annotation=str,
    )
    return handler


def make_retail_tools(env: RetailEnv, allowed_tools: list[str] | None = None) -> list[Any]:
    """Register canonical retail tools whose bodies only forward to RetailEnv."""
    from agents import function_tool

    tools: list[Any] = []
    for spec in build_tool_specs(env, allowed_tools):
        handler = _build_tool_function(
            spec["name"],
            spec["description"],
            spec["args_schema"],
            spec["invoke"],
        )
        tools.append(function_tool(handler))
    return tools
