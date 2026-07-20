#!/usr/bin/env python3
"""Validate and summarize CrewAI AgentRunResult JSONL rows without ranking."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import fields
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adapter.schemas import AgentRunResult
from adapter.validation import validate_task_output, validate_tool_call_constraints


_MODEL_FIELDS = {field.name for field in fields(AgentRunResult)}
_IMPORTANT_METADATA = (
    "run_id",
    "experiment_id",
    "framework_version",
    "model_provider",
    "model_name",
    "temperature",
    "prompt_version",
    "started_at",
    "completed_at",
    "raw_output",
)
_OPTIONAL_STRING_FIELDS = (
    "error",
    "case_id",
    "run_id",
    "experiment_id",
    "framework_version",
    "model_provider",
    "model_name",
    "model_version",
    "prompt_version",
    "started_at",
    "completed_at",
    "raw_output",
)


@lru_cache(maxsize=1)
def _tool_call_validator():
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("jsonschema is required for result validation") from exc
    schema = json.loads(
        (ROOT / "schemas" / "tool_call.schema.json").read_text(encoding="utf-8")
    )
    return jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )


def _input_paths(values: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        if value.is_file():
            paths.append(value)
        elif value.is_dir():
            paths.extend(sorted(value.glob("*.jsonl")))
        else:
            raise FileNotFoundError(f"result file or directory not found: {value}")
    return paths


def _row_model_errors(row: dict[str, Any], result: AgentRunResult) -> list[str]:
    errors: list[str] = []
    unknown = sorted(set(row) - _MODEL_FIELDS)
    missing = sorted(_MODEL_FIELDS - set(row))
    if unknown:
        errors.append(f"unknown AgentRunResult fields: {unknown}")
    if missing:
        errors.append(f"missing AgentRunResult fields: {missing}")
    if result.framework != "crewai":
        errors.append(f"framework must be 'crewai', found {result.framework!r}")
    for field_name in ("task_id", "framework", "vertical", "final_output"):
        if not isinstance(getattr(result, field_name), str):
            errors.append(f"{field_name} must be a string")
    for field_name in _OPTIONAL_STRING_FIELDS:
        value = getattr(result, field_name)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field_name} must be a string or null")
    if not isinstance(result.success, bool):
        errors.append("success must be a boolean")
    if (
        isinstance(result.latency_seconds, bool)
        or not isinstance(result.latency_seconds, (int, float))
        or result.latency_seconds < 0
    ):
        errors.append("latency_seconds must be a non-negative number")
    if (
        result.temperature is not None
        and (
            isinstance(result.temperature, bool)
            or not isinstance(result.temperature, (int, float))
        )
    ):
        errors.append("temperature must be a number or null")
    if (
        result.max_output_tokens is not None
        and (
            isinstance(result.max_output_tokens, bool)
            or not isinstance(result.max_output_tokens, int)
            or result.max_output_tokens < 0
        )
    ):
        errors.append("max_output_tokens must be a non-negative integer or null")
    if result.seed is not None and (
        isinstance(result.seed, bool) or not isinstance(result.seed, int)
    ):
        errors.append("seed must be an integer or null")
    if not isinstance(result.raw_metadata, dict):
        errors.append("raw_metadata must be an object")
    if not isinstance(result.tool_calls, list):
        errors.append("tool_calls must be an array")
    if not isinstance(result.token_usage, dict):
        errors.append("token_usage must be an object")
    if (
        result.tool_call_count is not None
        and (
            isinstance(result.tool_call_count, bool)
            or not isinstance(result.tool_call_count, int)
            or result.tool_call_count < 0
        )
    ):
        errors.append("tool_call_count must be a non-negative integer or null")
    if isinstance(result.tool_calls, list):
        if result.tool_call_count != len(result.tool_calls):
            errors.append("tool_call_count does not match tool_calls length")
        for index, call in enumerate(result.tool_calls):
            if not isinstance(call, dict):
                errors.append(f"tool_calls[{index}] must be an object")
                continue
            for schema_error in sorted(
                _tool_call_validator().iter_errors(call),
                key=lambda error: str(list(error.path)),
            ):
                location = ".".join(str(part) for part in schema_error.path) or "<root>"
                errors.append(
                    f"tool_calls[{index}] schema {location}: {schema_error.message}"
                )
            for error in validate_tool_call_constraints(call):
                errors.append(f"tool_calls[{index}]: {error}")
    return errors


def inspect_rows(paths: list[Path]) -> tuple[dict[str, Any], list[str]]:
    summary: dict[str, Any] = {
        "rows": 0,
        "task_counts": Counter(),
        "success": 0,
        "failure": 0,
        "missing_token_usage": Counter(),
        "missing_metadata": Counter(),
        "tool_outcomes": Counter(),
        "malformed_outputs": [],
        "duplicate_case_ids": [],
    }
    errors: list[str] = []
    seen_case_ids: set[tuple[str | None, str]] = set()
    duplicate_case_ids: set[str] = set()

    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                location = f"{path}:{line_number}"
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{location}: invalid JSON: {exc}")
                    continue
                if not isinstance(row, dict):
                    errors.append(f"{location}: row must be a JSON object")
                    continue
                try:
                    result = AgentRunResult(**row)
                except TypeError as exc:
                    errors.append(f"{location}: AgentRunResult rejected row: {exc}")
                    continue

                summary["rows"] += 1
                if isinstance(result.task_id, str):
                    summary["task_counts"][result.task_id] += 1
                if result.success is True:
                    summary["success"] += 1
                elif result.success is False:
                    summary["failure"] += 1
                try:
                    model_errors = _row_model_errors(row, result)
                except Exception as exc:
                    model_errors = [
                        f"validation failed: {type(exc).__name__}: {exc}"
                    ]
                for error in model_errors:
                    errors.append(f"{location}: {error}")

                if (
                    isinstance(result.case_id, str)
                    and result.case_id
                    and (
                        result.experiment_id is None
                        or isinstance(result.experiment_id, str)
                    )
                ):
                    case_key = (result.experiment_id, result.case_id)
                    if case_key in seen_case_ids:
                        duplicate_case_ids.add(result.case_id)
                    seen_case_ids.add(case_key)

                usage = result.token_usage if isinstance(result.token_usage, dict) else {}
                for field_name in ("input_tokens", "output_tokens", "total_tokens"):
                    value = usage.get(field_name)
                    if value is None:
                        summary["missing_token_usage"][field_name] += 1
                    elif isinstance(value, bool) or not isinstance(value, int) or value < 0:
                        errors.append(
                            f"{location}: token_usage.{field_name} must be a "
                            "non-negative integer or null"
                        )

                if all(isinstance(usage.get(name), int) for name in (
                    "input_tokens", "output_tokens", "total_tokens"
                )):
                    if usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]:
                        errors.append(f"{location}: inconsistent token total")

                for field_name in _IMPORTANT_METADATA:
                    if getattr(result, field_name, None) is None:
                        summary["missing_metadata"][field_name] += 1

                if isinstance(result.tool_calls, list):
                    for call in result.tool_calls:
                        if isinstance(call, dict):
                            outcome = call.get("outcome", "missing")
                            summary["tool_outcomes"][
                                outcome if isinstance(outcome, str) else "invalid"
                            ] += 1

                if result.success is True or result.final_output:
                    try:
                        parsed = json.loads(result.final_output)
                        if not isinstance(parsed, dict):
                            raise ValueError("final output is not a JSON object")
                        schema_errors = validate_task_output(result.task_id, parsed)
                        if schema_errors:
                            raise ValueError(
                                "output schema: " + "; ".join(schema_errors)
                            )
                    except Exception as exc:
                        message = f"{type(exc).__name__}: {exc}"
                        summary["malformed_outputs"].append(
                            {
                                "case_id": result.case_id,
                                "task_id": result.task_id,
                                "error": message,
                            }
                        )
                        errors.append(f"{location}: malformed final output: {message}")

    summary["duplicate_case_ids"] = sorted(duplicate_case_ids)
    if duplicate_case_ids:
        errors.append(f"duplicate case IDs: {sorted(duplicate_case_ids)}")
    return summary, errors


def _counter_text(counter: Counter) -> str:
    return " ".join(f"{key}={counter[key]}" for key in sorted(counter)) or "none"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        nargs="+",
        required=True,
        help="One or more AgentRunResult JSONL files or directories.",
    )
    args = parser.parse_args()
    try:
        paths = _input_paths(args.input)
    except Exception as exc:
        print(f"INPUT_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if not paths:
        print("INPUT_ERROR no JSONL files found", file=sys.stderr)
        return 2

    summary, errors = inspect_rows(paths)
    print(f"ROWS {summary['rows']}")
    print(f"TASK_COUNTS {_counter_text(summary['task_counts'])}")
    print(f"RUN_STATUS success={summary['success']} failure={summary['failure']}")
    print(f"MISSING_TOKEN_USAGE {_counter_text(summary['missing_token_usage'])}")
    print(f"MISSING_METADATA {_counter_text(summary['missing_metadata'])}")
    print(f"TOOL_OUTCOMES {_counter_text(summary['tool_outcomes'])}")
    print(f"DUPLICATE_CASE_IDS {summary['duplicate_case_ids'] or 'none'}")
    print(f"MALFORMED_FINAL_OUTPUTS {len(summary['malformed_outputs'])}")
    for item in summary["malformed_outputs"]:
        print(
            f"MALFORMED case={item['case_id']} task={item['task_id']} "
            f"error={item['error']}"
        )
    for error in errors:
        print(f"INVALID {error}", file=sys.stderr)
    print(f"CHECK_COMPLETE validation_errors={len(errors)} rankings_calculated=0")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
