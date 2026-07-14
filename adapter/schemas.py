from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkTask:
    task_id: str
    vertical: str
    prompt: str
    expected_output_type: str = "json"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    task_id: str
    framework: str
    vertical: str
    final_output: str
    latency_seconds: float
    success: bool
    error: str | None = None
    tool_call_count: int | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
