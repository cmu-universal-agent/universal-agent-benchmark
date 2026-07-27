"""Trace/result dataclasses shared by env.py, trace.py, and the wrappers.

Field names here are placeholders pending Jessica's canonical contract v1
(see WS3 build guide, section 1). Swap names/shapes when the contract
freezes -- callers should only depend on the dataclass fields, not on any
particular serialization helper.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    state_changed: bool = False


@dataclass
class ToolCallRecord:
    index: int
    tool_name: str
    arguments: dict[str, Any]
    ok: bool
    error_code: str | None
    state_changed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "ok": self.ok,
            "error_code": self.error_code,
            "state_changed": self.state_changed,
        }
