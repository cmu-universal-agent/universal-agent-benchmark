"""CrewAI BaseTool bindings for WS3 tau-retail canonical tools."""

from __future__ import annotations

from collections.abc import Callable
import sys
from typing import Any

from pydantic import BaseModel, PrivateAttr

from adapter.retail_core.env import RetailEnv
from adapter.retail_tool_factory import build_tool_specs

# Import the existing runner first so CrewAI's storage and telemetry settings
# are configured before the package initializes.
from frameworks.crewai_agent import run as _crewai_runtime  # noqa: F401

from crewai.tools import BaseTool


class RetailTool(BaseTool):
    """CrewAI-native tool whose implementation only forwards to RetailEnv."""

    _invoke: Callable[..., dict[str, Any]] = PrivateAttr()

    def __init__(
        self,
        *,
        name: str,
        description: str,
        args_schema: type[BaseModel],
        invoke: Callable[..., dict[str, Any]],
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            args_schema=args_schema,
        )
        self._invoke = invoke

    def _run(self, **arguments: Any) -> dict[str, Any]:
        print(
            f"CREWAI_PROGRESS phase=tool_start tool={self.name}",
            file=sys.stderr,
            flush=True,
        )
        try:
            return self._invoke(**arguments)
        finally:
            print(
                f"CREWAI_PROGRESS phase=tool_end tool={self.name}",
                file=sys.stderr,
                flush=True,
            )


def make_retail_tools(
    env: RetailEnv,
    allowed_tools: list[str] | None = None,
) -> list[BaseTool]:
    """Register canonical retail tools through CrewAI's native tool layer."""
    return [
        RetailTool(
            name=spec["name"],
            description=spec["description"],
            args_schema=spec["args_schema"],
            invoke=spec["invoke"],
        )
        for spec in build_tool_specs(env, allowed_tools)
    ]


def invoke_retail_tool(
    tools: list[BaseTool],
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Invoke one registered CrewAI tool for offline wrapper validation."""
    tool_by_name = {tool.name: tool for tool in tools}
    if name not in tool_by_name:
        raise KeyError(f"tool not registered: {name}")
    return tool_by_name[name].to_structured_tool().invoke(arguments)
