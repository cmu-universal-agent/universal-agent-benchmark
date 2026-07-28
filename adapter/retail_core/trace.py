"""Ordered, lossless recording of every call_tool invocation.

Builds the exact list adapter.runtime.normalize_tool_calls() expects,
reusing the same bounded-result/hash/schema_version logic every other
vertical relies on, so retail tool calls end up schema-identical to
schemas/tool_call.schema.json without retail_core re-deriving that shape
itself. tool_call_id is pre-assigned at record() time (normalize_tool_calls
only fills it via setdefault) so it stays stable no matter how many times
get_trace()/get_session_evidence() re-normalize the accumulated log.
"""

from __future__ import annotations

import uuid
from typing import Any

from adapter.runtime import normalize_tool_calls


class Trace:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._raw: list[dict[str, Any]] = []
        self._state_before: list[str] = []
        self._state_after: list[str] = []

    def record(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        was_allowed: bool,
        arguments_valid: bool,
        started_at: str,
        completed_at: str,
        latency_ms: int,
        outcome: str,
        result: Any,
        error: dict[str, Any] | None,
        state_before_sha256: str,
        state_after_sha256: str,
        retry_of: str | None = None,
    ) -> str:
        tool_call_id = f"tool-{uuid.uuid4().hex}"
        self._raw.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "was_allowed": was_allowed,
                "arguments_valid": arguments_valid,
                "started_at": started_at,
                "completed_at": completed_at,
                "latency_ms": latency_ms,
                "outcome": outcome,
                "result": result,
                "error": error,
                "retry_of": retry_of,
            }
        )
        self._state_before.append(state_before_sha256)
        self._state_after.append(state_after_sha256)
        return tool_call_id

    def to_tool_calls(self) -> list[dict[str, Any]]:
        """schemas/tool_call.schema.json-conformant records, run-wide order."""
        return normalize_tool_calls(self._raw, self.run_id)

    def to_session_events(self) -> list[dict[str, Any]]:
        """schemas/tau_retail_session_evidence.schema.json 'events' entries."""
        calls = self.to_tool_calls()
        return [
            {
                "state_before_sha256": self._state_before[index],
                "call": call,
                "state_after_sha256": self._state_after[index],
            }
            for index, call in enumerate(calls)
        ]

    def __len__(self) -> int:
        return len(self._raw)
