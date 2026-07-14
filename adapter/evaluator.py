import json
from typing import Any

from adapter.schemas import AgentRunResult


def evaluate_result(
    result: AgentRunResult,
    required_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Compute simple pass/fail metrics for a single AgentRunResult."""
    parsed_output: Any = None
    json_valid = False
    try:
        parsed_output = json.loads(result.final_output)
        json_valid = True
    except (json.JSONDecodeError, TypeError):
        pass

    missing_keys: list[str] = []
    if required_keys:
        if json_valid and isinstance(parsed_output, dict):
            missing_keys = [key for key in required_keys if key not in parsed_output]
        else:
            missing_keys = list(required_keys)

    error_type = None
    if result.error:
        error_type = result.error.split(":", 1)[0].strip()

    return {
        "task_id": result.task_id,
        "framework": result.framework,
        "vertical": result.vertical,
        "success": result.success,
        "latency_seconds": result.latency_seconds,
        "json_valid": json_valid,
        "required_keys_present": not missing_keys,
        "missing_keys": missing_keys,
        "error_type": error_type,
    }
