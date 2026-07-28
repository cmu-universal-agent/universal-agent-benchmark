"""Result dataclass shared by tools.py, env.py, and the wrappers.

State-record and tool-call shapes are NOT dataclasses here: they must match
schemas/tau_retail_state_record.schema.json and schemas/tool_call.schema.json
exactly, so db.py and trace.py build them as plain dicts (the latter via
adapter.runtime.normalize_tool_calls, the same helper every other vertical
uses) rather than through a bespoke shape that could drift from the schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    data: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None
    state_changed: bool = False
