#!/usr/bin/env python3
"""Validate generated core-pilot cases, gold linkage, and leakage boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.validation import find_evaluator_leakage

DEFAULT_INPUT = ROOT / "data" / "generated" / "core_pilot"
SCHEMA_PATH = ROOT / "schemas" / "benchmark_case.schema.json"
GOLD_SCHEMA_PATH = ROOT / "schemas" / "gold_record.schema.json"
TASK_IDS = {"H1", "H2", "H4", "H5", "E1", "E2", "E3", "E5"}


def _task_gold_errors(row: dict) -> list[str]:
    task_id = row.get("task_id")
    gold = row.get("gold")
    if not isinstance(gold, dict) or not gold:
        return ["gold payload must not be empty"]

    errors: list[str] = []
    result = gold.get("result")
    result_fields = {
        "H1": ("decision",),
        "H2": ("urgency",),
        "H4": ("symptoms", "history", "risks", "next_steps"),
        "H5": ("boundary_action",),
        "E1": ("trend_direction",),
        "E2": ("recommendations", "constraints_satisfied"),
        "E3": ("decision",),
    }
    required_result_fields = result_fields.get(task_id)
    if required_result_fields is not None:
        if not isinstance(result, dict):
            errors.append(f"{task_id} gold must contain a result object")
        else:
            missing = [
                field for field in required_result_fields if field not in result
            ]
            if missing:
                errors.append(f"{task_id} gold result is missing fields: {missing}")

    if task_id == "E3" and not isinstance(gold.get("expected_actions"), list):
        errors.append("E3 gold must contain expected_actions")
    if task_id == "E5":
        expected_actions = gold.get("expected_actions")
        if not isinstance(expected_actions, list) or not expected_actions:
            errors.append("E5 gold expected_actions must not be empty")
        if not isinstance(gold.get("expected_communications"), list):
            errors.append("E5 gold must contain expected_communications")
        if not isinstance(gold.get("state_validation"), str) or not gold[
            "state_validation"
        ].strip():
            errors.append("E5 gold must contain state_validation")
    return errors


def _load_required_artifact(
    input_path: Path,
    name: str,
    errors: list[str],
) -> dict | None:
    path = input_path / name
    if not path.is_file():
        errors.append(f"missing required artifact: {name}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{name}: {type(exc).__name__}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{name}: expected a JSON object")
        return None
    return value


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
    gold_schema = json.loads(GOLD_SCHEMA_PATH.read_text(encoding="utf-8"))
    gold_validator = jsonschema.Draft202012Validator(
        gold_schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    errors: list[str] = []
    cases: dict[str, dict] = {}
    counts = Counter()
    cases_dir = args.input / "cases"
    case_paths = sorted(cases_dir.glob("task_*.json"))
    if not cases_dir.is_dir():
        errors.append(f"missing cases directory: {cases_dir}")
    elif not case_paths:
        errors.append(f"no generated case files in: {cases_dir}")
    for path in case_paths:
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
            continue
        case_id = case.get("case_id", path.name)
        if case_id in cases:
            errors.append(f"duplicate case_id: {case_id}")
        cases[case_id] = case
        counts[case.get("task_id", "<missing>")] += 1
        for error in validator.iter_errors(case):
            location = ".".join(str(value) for value in error.path) or "<root>"
            errors.append(f"{path.name} [{location}]: {error.message}")
        leaked = sorted({key for key, _ in find_evaluator_leakage(case)})
        if leaked:
            errors.append(f"{path.name}: evaluator-only keys leaked into case: {leaked}")

    gold: dict[str, dict] = {}
    gold_counts = Counter()
    gold_dir = args.input / "gold"
    gold_paths = sorted(gold_dir.glob("*.jsonl"))
    if not gold_dir.is_dir():
        errors.append(f"missing gold directory: {gold_dir}")
    elif not gold_paths:
        errors.append(f"no generated gold files in: {gold_dir}")
    for path in gold_paths:
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
            gold_counts[row.get("task_id", "<missing>")] += 1
            for error in gold_validator.iter_errors(row):
                location = ".".join(str(value) for value in error.path) or "<root>"
                errors.append(
                    f"{path.name}:{line_number} [{location}]: {error.message}"
                )
            for error in _task_gold_errors(row):
                errors.append(f"{path.name}:{line_number}: {error}")

    missing_gold = sorted(set(cases) - set(gold))
    orphan_gold = sorted(set(gold) - set(cases))
    if missing_gold:
        errors.append(f"cases missing gold: {missing_gold}")
    if orphan_gold:
        errors.append(f"gold without cases: {orphan_gold}")
    for case_id in set(cases) & set(gold):
        if cases[case_id]["task_id"] != gold[case_id].get("task_id"):
            errors.append(f"task mismatch for {case_id}")
        case_metadata = cases[case_id].get("metadata", {})
        gold_source = gold[case_id].get("source", {})
        for case_field, source_field in (
            ("dataset", "dataset"),
            ("source_record_id", "source_record_id"),
            ("source_split", "source_split"),
        ):
            if case_metadata.get(case_field) != gold_source.get(source_field):
                errors.append(
                    f"case/gold {source_field} mismatch for {case_id}"
                )

    generated_tasks = set(counts)
    unknown_tasks = generated_tasks - TASK_IDS
    if unknown_tasks:
        errors.append(f"unknown task IDs: {sorted(unknown_tasks)}")
    missing_tasks = TASK_IDS - generated_tasks
    if missing_tasks:
        errors.append(f"missing task IDs: {sorted(missing_tasks)}")
    for task_id in sorted(TASK_IDS):
        count = counts[task_id]
        if count != args.expected_per_task:
            errors.append(
                f"{task_id}: expected {args.expected_per_task} cases, found {count}"
            )
        if gold_counts[task_id] != args.expected_per_task:
            errors.append(
                f"{task_id}: expected {args.expected_per_task} gold records, "
                f"found {gold_counts[task_id]}"
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

    manifest = _load_required_artifact(
        args.input,
        "split_manifest.json",
        errors,
    )
    manifest_case_ids: set[str] = set()
    if manifest is not None:
        manifest_tasks = manifest.get("tasks")
        if (
            manifest.get("schema_version") != "1.0"
            or manifest.get("status") != "local_review_manifest"
            or not isinstance(manifest.get("seed"), int)
            or not isinstance(manifest_tasks, dict)
        ):
            errors.append("split_manifest.json does not match the production contract")
        else:
            manifest_task_ids = set(manifest_tasks)
            if manifest_task_ids != TASK_IDS:
                errors.append(
                    "manifest task IDs do not match core tasks: "
                    f"{sorted(manifest_task_ids)}"
                )
            for task_id in sorted(TASK_IDS):
                entries = manifest_tasks.get(task_id, [])
                if not isinstance(entries, list):
                    errors.append(f"manifest {task_id} entries must be an array")
                    continue
                if len(entries) != counts[task_id]:
                    errors.append(
                        f"manifest {task_id} count mismatch: "
                        f"expected {counts[task_id]}, found {len(entries)}"
                    )
                for entry in entries:
                    if not isinstance(entry, dict):
                        errors.append(f"manifest {task_id} entry must be an object")
                        continue
                    case_id = entry.get("case_id")
                    if case_id in manifest_case_ids:
                        errors.append(f"duplicate manifest case_id: {case_id}")
                    if isinstance(case_id, str):
                        manifest_case_ids.add(case_id)
                    case = cases.get(case_id)
                    if case is None:
                        continue
                    metadata = case.get("metadata", {})
                    expected_entry = {
                        "case_id": case_id,
                        "source_record_id": metadata.get("source_record_id"),
                        "source_split": metadata.get("source_split"),
                        "benchmark_split": metadata.get("split"),
                    }
                    if entry != expected_entry or case.get("task_id") != task_id:
                        errors.append(f"manifest metadata mismatch for {case_id}")
            if manifest_case_ids != set(cases):
                errors.append("manifest case IDs do not match generated cases")
            if manifest.get("total_cases") != len(cases):
                errors.append(
                    "manifest total_cases mismatch: "
                    f"expected {len(cases)}, found {manifest.get('total_cases')}"
                )

    report = _load_required_artifact(
        args.input,
        "coverage_report.json",
        errors,
    )
    if report is not None:
        report_tasks = report.get("tasks")
        if (
            report.get("schema_version") != "1.0"
            or report.get("status") != "review_samples_not_approved"
            or not isinstance(report.get("generator"), str)
            or not report.get("generator")
            or not isinstance(report.get("seed"), int)
            or not isinstance(report.get("known_gaps"), list)
            or not isinstance(report_tasks, dict)
        ):
            errors.append("coverage_report.json does not match the production contract")
        else:
            report_task_ids = set(report_tasks)
            if report_task_ids != TASK_IDS:
                errors.append(
                    "coverage task IDs do not match core tasks: "
                    f"{sorted(report_task_ids)}"
                )
            if report.get("requested_per_task") != args.expected_per_task:
                errors.append(
                    "coverage requested_per_task mismatch: "
                    f"expected {args.expected_per_task}, "
                    f"found {report.get('requested_per_task')}"
                )
            for task_id in sorted(TASK_IDS):
                status = report_tasks.get(task_id)
                if not isinstance(status, dict):
                    errors.append(f"coverage {task_id} status must be an object")
                    continue
                if status.get("status") != "generated_for_review":
                    errors.append(f"coverage {task_id} is not generated_for_review")
                if status.get("cases") != counts[task_id]:
                    errors.append(
                        f"coverage {task_id} case count mismatch: "
                        f"expected {counts[task_id]}, found {status.get('cases')}"
                    )
                if status.get("gold_records") != gold_counts[task_id]:
                    errors.append(
                        f"coverage {task_id} gold count mismatch: "
                        f"expected {gold_counts[task_id]}, "
                        f"found {status.get('gold_records')}"
                    )
            if report.get("total_cases") != len(cases):
                errors.append(
                    "coverage total_cases mismatch: "
                    f"expected {len(cases)}, found {report.get('total_cases')}"
                )
            if report.get("total_gold_records") != len(gold):
                errors.append(
                    "coverage total_gold_records mismatch: "
                    f"expected {len(gold)}, "
                    f"found {report.get('total_gold_records')}"
                )
            if (
                manifest is not None
                and report.get("seed") != manifest.get("seed")
            ):
                errors.append("coverage and manifest seeds do not match")

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
