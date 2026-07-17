#!/usr/bin/env python3
"""Validate generated core-pilot cases, gold linkage, and leakage boundaries."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "generated" / "core_pilot"
SCHEMA_PATH = ROOT / "schemas" / "benchmark_case.schema.json"
TASK_IDS = {"H1", "H2", "H4", "H5", "E1", "E2", "E3", "E5"}
FORBIDDEN_KEYS = {
    "gold",
    "ground_truth",
    "rubric",
    "rubrics",
    "expected_actions",
    "evaluation_criteria",
    "safe_response",
    "reference_safe_response",
    "note",
    "canary",
}


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _keys(child)}
    return set()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--expected-per-task", type=int, default=8)
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("jsonschema is required") from exc

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    errors: list[str] = []
    cases: dict[str, dict] = {}
    counts = Counter()
    for path in sorted((args.input / "cases").glob("task_*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        case_id = case.get("case_id", path.name)
        if case_id in cases:
            errors.append(f"duplicate case_id: {case_id}")
        cases[case_id] = case
        counts[case.get("task_id", "<missing>")] += 1
        for error in validator.iter_errors(case):
            location = ".".join(str(value) for value in error.path) or "<root>"
            errors.append(f"{path.name} [{location}]: {error.message}")
        leaked = sorted(_keys(case) & FORBIDDEN_KEYS)
        if leaked:
            errors.append(f"{path.name}: evaluator-only keys leaked into case: {leaked}")

    gold: dict[str, dict] = {}
    for path in sorted((args.input / "gold").glob("*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{line_number}: {exc}")
                continue
            case_id = row.get("case_id")
            if case_id in gold:
                errors.append(f"duplicate gold case_id: {case_id}")
            gold[case_id] = row

    missing_gold = sorted(set(cases) - set(gold))
    orphan_gold = sorted(set(gold) - set(cases))
    if missing_gold:
        errors.append(f"cases missing gold: {missing_gold}")
    if orphan_gold:
        errors.append(f"gold without cases: {orphan_gold}")
    for case_id in set(cases) & set(gold):
        if cases[case_id]["task_id"] != gold[case_id].get("task_id"):
            errors.append(f"task mismatch for {case_id}")

    generated_tasks = set(counts)
    unknown_tasks = generated_tasks - TASK_IDS
    if unknown_tasks:
        errors.append(f"unknown task IDs: {sorted(unknown_tasks)}")
    for task_id, count in sorted(counts.items()):
        if count != args.expected_per_task:
            errors.append(
                f"{task_id}: expected {args.expected_per_task} cases, found {count}"
            )
    e5_tool_sets = {
        tuple(case.get("allowed_tools", []))
        for case in cases.values()
        if case.get("task_id") == "E5"
    }
    if len(e5_tool_sets) > 1:
        errors.append("E5 cases do not expose one identical full tool registry")
    if e5_tool_sets and len(next(iter(e5_tool_sets))) < 2:
        errors.append("E5 tool registry is unexpectedly empty or task-specific")

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        raise SystemExit(f"CORE_PILOT_INVALID errors={len(errors)}")
    print(
        "CORE_PILOT_OK "
        + " ".join(f"{task_id}={counts[task_id]}" for task_id in sorted(counts))
        + f" cases={len(cases)} gold={len(gold)} leakage=0"
    )


if __name__ == "__main__":
    main()
