"""Shared vertical routing for every framework adapter."""

from __future__ import annotations

from typing import TypeVar


Tool = TypeVar("Tool")

RUNTIME_VERTICALS = {
    "healthcare": "medical_diagnostic",
    "ecommerce": "ecommerce_trend_research",
    "smoke_test": "smoke_test",
    "retail": "retail",
    "tau_retail": "retail",
}


def resolve_runtime_vertical(task_id: str, schema_vertical: str) -> str:
    """Map a benchmark vertical to its runtime, including stateful E5."""
    if task_id == "E5":
        return "retail"
    return RUNTIME_VERTICALS.get(schema_vertical, schema_vertical)


def select_vertical_tools(
    tools_by_vertical: dict[str, dict[str, Tool]],
    vertical: str,
    allowed_tools: list[str] | None,
) -> list[Tool]:
    """Return only tools registered for the resolved vertical and allow-list."""
    available = tools_by_vertical.get(vertical, {})
    if allowed_tools is None:
        return list(available.values())
    allowed = set(allowed_tools)
    return [tool for name, tool in available.items() if name in allowed]
