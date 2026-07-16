#!/usr/bin/env python3
"""Validate draft schema fixtures and framework-neutral semantic contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.validation import (
    validate_benchmark_case_constraints,
    validate_run_log_constraints,
    validate_tool_call_constraints,
)

FIXTURES_PATH = ROOT / "tests" / "fixtures" / "schema_cases.json"
SCHEMA_DIR = ROOT / "schemas"


def _all_errors(error: Any) -> Iterable[Any]:
    yield error
    for child in error.context:
        yield from _all_errors(child)


def _semantic_errors(schema_name: str, document: dict[str, Any]) -> list[str]:
    if schema_name == "benchmark_case.schema.json":
        return validate_benchmark_case_constraints(document)
    if schema_name == "tool_call.schema.json":
        return validate_tool_call_constraints(document)
    if schema_name == "run_log.schema.json":
        return validate_run_log_constraints(document)
    return []


def main() -> None:
    try:
        import jsonschema
        from referencing import Registry, Resource
    except ImportError as exc:
        raise SystemExit("jsonschema is required to validate fixtures") from exc

    payload = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    schema_documents = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in SCHEMA_DIR.glob("*.schema.json")
    }
    registry = Registry()
    for schema in schema_documents.values():
        jsonschema.Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    schema_cache: dict[str, Any] = {}
    failures: list[str] = []
    valid_count = 0
    invalid_count = 0

    for fixture in payload["fixtures"]:
        name = fixture["name"]
        schema_name = fixture["schema"]
        expected_valid = fixture["expected_valid"]
        document = fixture["document"]
        if schema_name not in schema_cache:
            schema = schema_documents[schema_name]
            schema_cache[schema_name] = jsonschema.Draft202012Validator(
                schema,
                registry=registry,
                format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
            )
        validator = schema_cache[schema_name]
        schema_errors = list(validator.iter_errors(document))
        semantic_errors = _semantic_errors(schema_name, document)
        is_valid = not schema_errors and not semantic_errors

        if expected_valid:
            valid_count += 1
            if not is_valid:
                details = [error.message for error in schema_errors]
                details.extend(semantic_errors)
                failures.append(f"{name}: expected valid; got {details}")
        else:
            invalid_count += 1
            if is_valid:
                failures.append(f"{name}: expected invalid; validation passed")
                continue
            expected_validator = fixture.get("expected_validator")
            if expected_validator and not any(
                nested.validator == expected_validator
                for error in schema_errors
                for nested in _all_errors(error)
            ):
                failures.append(
                    f"{name}: expected validator {expected_validator!r} was not observed"
                )

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)
    print(
        f"CONTRACT_FIXTURES_OK valid={valid_count} invalid={invalid_count} "
        f"schemas={len(schema_cache)}"
    )


if __name__ == "__main__":
    main()
