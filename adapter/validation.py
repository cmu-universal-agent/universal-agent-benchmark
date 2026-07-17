"""Shared semantic validation that cannot be expressed in one JSON Schema.

These helpers are framework-neutral. Dataset owners provide mapping contents;
the adapter and converter layers use these checks consistently.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ORDINARY_SOURCE_LIMIT = 50_000
LONG_CONTEXT_SOURCE_LIMIT = 100_000
TOOL_RESULT_MAX_BYTES = 50 * 1024
FORBIDDEN_AGENT_VISIBLE_KEYS = {
    "expected",
    "expected_answer",
    "gold_answer",
    "ground_truth",
    "rubric",
    "evaluator_rubric",
}
OUTPUT_SCHEMA_BY_TASK = {
    "H1": "medical_output.schema.json",
    "H2": "medical_output.schema.json",
    "H4": "medical_output.schema.json",
    "H5": "medical_output.schema.json",
    "E1": "ecommerce_output.schema.json",
    "E2": "ecommerce_output.schema.json",
    "E3": "ecommerce_output.schema.json",
    "E5": "ecommerce_output.schema.json",
}


def _walk_keys(value: Any, path: str = "<root>") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            found.append((str(key), child_path))
            found.extend(_walk_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_keys(child, f"{path}[{index}]"))
    return found


def validate_benchmark_case_constraints(case: dict[str, Any]) -> list[str]:
    """Check aggregate context limits and evaluator-data isolation."""
    errors: list[str] = []
    sources = case.get("input", {}).get("source_documents", []) or []
    total = sum(len(str(source.get("content", ""))) for source in sources)
    limit = (
        LONG_CONTEXT_SOURCE_LIMIT
        if case.get("stress_type") == "long_context"
        else ORDINARY_SOURCE_LIMIT
    )
    if total > limit:
        errors.append(
            f"aggregate source content is {total} characters; limit is {limit}"
        )

    for key, path in _walk_keys(case):
        if key.lower() in FORBIDDEN_AGENT_VISIBLE_KEYS:
            errors.append(f"agent-visible case contains forbidden key at {path}")
    return errors


@lru_cache(maxsize=2)
def _output_validator(schema_name: str):
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("jsonschema is required for output validation") from exc

    path = ROOT / "schemas" / schema_name
    schema = json.loads(path.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )


def validate_task_output(
    task_id: str, output: dict[str, Any]
) -> list[str] | None:
    """Validate one parsed task output against its vertical schema.

    ``None`` means no task-specific output schema applies (for example, a
    legacy smoke task). An empty list means the applicable schema passed.
    """
    schema_name = OUTPUT_SCHEMA_BY_TASK.get(task_id)
    if schema_name is None:
        return None
    validator = _output_validator(schema_name)
    errors = sorted(validator.iter_errors(output), key=lambda error: list(error.path))
    rendered = []
    for error in errors:
        location = ".".join(str(part) for part in error.path) or "<root>"
        rendered.append(f"{location}: {error.message}")
    return rendered


def validate_tool_arguments(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    schema_dir: Path | None = None,
) -> list[str]:
    """Validate arguments against a canonical tool schema.

    Missing schemas are errors, rather than silently treating arguments as
    valid. Actual tool schemas are added only after the tool registry is
    confirmed.
    """
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("jsonschema is required for tool validation") from exc

    directory = schema_dir or ROOT / "tools" / "schemas"
    path = directory / f"{tool_name}.schema.json"
    if not path.exists():
        return [f"missing canonical tool schema: {path}"]
    schema = json.loads(path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [error.message for error in validator.iter_errors(arguments)]


def validate_tool_call_constraints(call: dict[str, Any]) -> list[str]:
    """Check retry and bounded-result metadata for one normalized call."""
    errors: list[str] = []
    if call.get("retry_of") == call.get("tool_call_id"):
        errors.append("retry_of must not point to the same tool_call_id")

    stored = json.dumps(
        call.get("result"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    if len(stored) > TOOL_RESULT_MAX_BYTES:
        errors.append("stored tool result exceeds the 50KB serialized limit")

    truncated = call.get("result_truncated")
    original_bytes = call.get("result_bytes")
    digest = call.get("result_sha256")
    if truncated:
        if not isinstance(original_bytes, int) or original_bytes <= TOOL_RESULT_MAX_BYTES:
            errors.append("truncated result must record original result_bytes > 50KB")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append("truncated result must record a SHA-256 digest")
    else:
        if digest is not None:
            errors.append("non-truncated result_sha256 must be null")
        if original_bytes != len(stored):
            errors.append("non-truncated result_bytes must equal stored serialized bytes")
    return errors


def validate_run_log_constraints(run_log: dict[str, Any]) -> list[str]:
    """Check cross-field relationships inside a normalized run log."""
    errors: list[str] = []
    usage = run_log.get("token_usage", {})
    values = [
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        usage.get("total_tokens"),
    ]
    if all(isinstance(value, int) for value in values):
        if values[0] + values[1] != values[2]:
            errors.append("token_usage.total_tokens must equal input + output")

    calls = run_log.get("tool_calls", []) or []
    indices: list[int] = []
    known_ids = {call.get("tool_call_id") for call in calls}
    for call in calls:
        if call.get("run_id") != run_log.get("run_id"):
            errors.append("tool call run_id does not match run log")
        if isinstance(call.get("sequence_index"), int):
            indices.append(call["sequence_index"])
        retry_of = call.get("retry_of")
        if retry_of is not None and retry_of not in known_ids:
            errors.append(f"retry_of references unknown tool_call_id: {retry_of}")
        errors.extend(validate_tool_call_constraints(call))
    if indices != list(range(len(calls))):
        errors.append("tool-call sequence_index values must be contiguous from zero")
    return errors


def validate_case_run_links(
    case: dict[str, Any], run_log: dict[str, Any]
) -> list[str]:
    """Check identifiers shared between an agent-visible case and its run."""
    errors: list[str] = []
    for field in ("case_id", "task_id", "vertical"):
        if case.get(field) != run_log.get(field):
            errors.append(f"case/run {field} mismatch")
    return errors
