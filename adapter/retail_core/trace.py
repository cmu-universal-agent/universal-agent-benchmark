"""Ordered, lossless recording of every call_tool invocation."""

from typing import Any

from adapter.retail_core.schemas import ToolCallRecord, ToolResult


class Trace:
    def __init__(self) -> None:
        self._records: list[ToolCallRecord] = []

    def record(self, tool_name: str, arguments: dict[str, Any], result: ToolResult) -> ToolCallRecord:
        entry = ToolCallRecord(
            index=len(self._records),
            tool_name=tool_name,
            arguments=arguments,
            ok=result.ok,
            error_code=result.error_code,
            state_changed=result.state_changed,
        )
        self._records.append(entry)
        return entry

    def to_list(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self._records]

    def clear(self) -> None:
        self._records = []
