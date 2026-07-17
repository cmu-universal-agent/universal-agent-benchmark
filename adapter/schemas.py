from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkTask:
    task_id: str
    vertical: str
    prompt: str
    expected_output_type: str = "json"
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str | None = None
    case_id: str | None = None
    allowed_tools: list[str] | None = None
    stress_type: str | None = None
    input_data: dict[str, Any] = field(default_factory=dict)


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
    case_id: str | None = None
    run_id: str | None = None
    experiment_id: str | None = None
    framework_version: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    seed: int | None = None
    prompt_version: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    raw_output: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    token_usage: dict[str, int | None] = field(
        default_factory=lambda: {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }
    )
