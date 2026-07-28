#!/usr/bin/env python3
"""Run approved core benchmark cases through CrewAI only."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.runtime import redact_error
from adapter.schemas import BenchmarkTask
from adapter.task_loader import load_task
from frameworks.crewai_agent.run import run_task


DEFAULT_CASES = ROOT / "data" / "generated" / "core_pilot" / "cases"
CORE_TASK_IDS = ("H1", "H2", "H4", "H5", "E1", "E2", "E3", "E5")
_TASK_ORDER = {task_id: index for index, task_id in enumerate(CORE_TASK_IDS)}


@dataclass(frozen=True)
class DiscoveredCase:
    path: Path
    task: BenchmarkTask


def _candidate_paths(value: Path) -> list[Path]:
    if value.is_file():
        return [value]
    if value.is_dir():
        # prepare_core_pilot.py writes a flat cases/task_*.json directory.
        return sorted(value.glob("*.json"))
    raise FileNotFoundError(f"case file or directory not found: {value}")


def discover_cases(value: Path) -> tuple[list[DiscoveredCase], list[str]]:
    """Load core cases and return them in deterministic task/case order."""
    discovered: list[DiscoveredCase] = []
    errors: list[str] = []
    for path in _candidate_paths(value):
        try:
            task = load_task(path)
        except Exception as exc:
            errors.append(f"{path}: {type(exc).__name__}: {exc}")
            continue
        if task.task_id not in _TASK_ORDER:
            errors.append(f"{path}: unsupported core task_id={task.task_id!r}")
            continue
        if not task.case_id:
            errors.append(f"{path}: core case is missing case_id")
            continue
        discovered.append(DiscoveredCase(path=path, task=task))

    discovered.sort(
        key=lambda item: (
            _TASK_ORDER[item.task.task_id],
            item.task.case_id or "",
            item.path.name,
        )
    )
    return discovered, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        type=Path,
        default=DEFAULT_CASES,
        help="One generated case JSON file or its flat cases directory.",
    )
    parser.add_argument(
        "--list-only",
        "--dry-run",
        dest="list_only",
        action="store_true",
        help="Discover and load cases without executing CrewAI or writing results.",
    )
    parser.add_argument(
        "--experiment-id",
        default=None,
        help="Stable experiment ID used for every case in this invocation.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override OPENAI_MODEL for this CrewAI-only invocation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional single JSONL destination passed to append_result.",
    )
    args = parser.parse_args()

    try:
        cases, discovery_errors = discover_cases(args.task)
    except Exception as exc:
        print(f"DISCOVERY_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    for error in discovery_errors:
        print(f"DISCOVERY_ERROR {error}", file=sys.stderr)
    if not cases:
        print("NO_CORE_CASES", file=sys.stderr)
        return 2

    counts = {task_id: 0 for task_id in CORE_TASK_IDS}
    seen_case_ids: set[str] = set()
    duplicate_case_ids: set[str] = set()
    for item in cases:
        counts[item.task.task_id] += 1
        case_id = item.task.case_id or ""
        if case_id in seen_case_ids:
            duplicate_case_ids.add(case_id)
        seen_case_ids.add(case_id)
        print(
            f"CASE {case_id} task={item.task.task_id} "
            f"vertical={item.task.vertical} path={item.path.name}"
        )

    if duplicate_case_ids:
        print(
            f"DUPLICATE_CASE_IDS {sorted(duplicate_case_ids)}",
            file=sys.stderr,
        )
        return 2

    print(
        "DISCOVERY_COUNTS "
        + " ".join(f"{task_id}={counts[task_id]}" for task_id in CORE_TASK_IDS)
        + f" total={len(cases)} errors={len(discovery_errors)}"
    )
    if args.list_only:
        print("LIST_ONLY_OK model_calls=0 result_writes=0")
        return 1 if discovery_errors else 0

    experiment_id = args.experiment_id or f"crewai-core-{uuid.uuid4().hex}"
    os.environ["BENCHMARK_EXPERIMENT_ID"] = experiment_id
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    print(f"EXPERIMENT {experiment_id}")

    completed = 0
    succeeded = 0
    failed = 0
    runner_errors = 0
    for item in cases:
        case_id = item.task.case_id or item.task.task_id
        print(f"RUN {case_id} task={item.task.task_id}")
        try:
            result = run_task(item.task)
            append_result(result, args.output)
        except Exception as exc:
            # A setup/serialization failure outside run_task must not prevent
            # later independent cases from running.
            runner_errors += 1
            error_message = redact_error(f"{type(exc).__name__}: {exc}")
            print(
                f"RUNNER_ERROR {case_id} {error_message}",
                file=sys.stderr,
            )
            continue
        completed += 1
        if result.success:
            succeeded += 1
        else:
            failed += 1
        print(
            f"RESULT {case_id} success={result.success} run_id={result.run_id} "
            f"experiment_id={result.experiment_id}"
        )

    print(
        f"CREWAI_CORE_COMPLETE discovered={len(cases)} completed={completed} "
        f"success={succeeded} failure={failed} runner_errors={runner_errors}"
    )
    return 1 if discovery_errors or runner_errors or failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
