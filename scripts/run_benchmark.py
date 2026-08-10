#!/usr/bin/env python3
"""Run one or more benchmark tasks through all three framework adapters.

Each framework runs in its own virtual environment via subprocess, writes its
AgentRunResult to results/metrics/<vertical>_results.jsonl, then this script
prints an aggregated evaluation summary per (task, framework) pair.
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.evaluator import evaluate_core_gold, evaluate_result
from adapter.e5_evaluator import evaluate_agent_result
from adapter.result_writer import default_result_path
from adapter.schemas import AgentRunResult
from adapter.task_loader import load_task
from adapter.tau_retail_env import TauReplayEnv

DEFAULT_TASK = ROOT / "verticals" / "smoke_test" / "task_001.json"
ATTEMPT_LEDGER = ROOT / "results" / "metrics" / "attempts.jsonl"


def _venv_python(venv_name: str) -> Path:
    """Return the platform-specific Python path for a local virtual environment."""
    venv_root = ROOT / venv_name
    windows_python = venv_root / "Scripts" / "python.exe"
    posix_python = venv_root / "bin" / "python"
    return windows_python if windows_python.exists() else posix_python


FRAMEWORKS = [
    (
        "openai_agents_sdk",
        _venv_python(".venv-openai"),
        ROOT / "frameworks" / "openai_agents_sdk" / "run.py",
    ),
    (
        "langgraph",
        _venv_python(".venv-langgraph"),
        ROOT / "frameworks" / "langgraph_agent" / "run.py",
    ),
    (
        "crewai",
        _venv_python(".venv-crewai"),
        ROOT / "frameworks" / "crewai_agent" / "run.py",
    ),
]


def _resolve_task_paths(task_arg: Path) -> list[Path]:
    if task_arg.is_dir():
        return sorted(task_arg.glob("*.json"))
    return [task_arg]


def _load_gold(task_arg: Path) -> dict[str, dict]:
    configured_e5_gold = os.getenv("BENCHMARK_E5_GOLD_PATH")
    if task_arg.is_file() and configured_e5_gold:
        gold_paths = [Path(configured_e5_gold)]
    else:
        gold_dir = (
            task_arg.parent / "gold"
            if task_arg.is_dir()
            else task_arg.parent.parent / "gold"
        )
        gold_paths = sorted(gold_dir.glob("*.jsonl")) if gold_dir.is_dir() else []
    rows = {}
    for path in gold_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["case_id"]] = row
    return rows


def _require_session_runs(
    rows: list[dict],
    *,
    expected: int,
    case_key: str,
    framework: str,
) -> list[dict]:
    if len(rows) != expected:
        raise RuntimeError(
            f"expected {expected} result rows for {case_key}/{framework}, "
            f"found {len(rows)}"
        )
    return rows


def _next_attempt(
    ledger: Path,
    logical_run_id: str,
    rerun_reason: str | None,
) -> int:
    prior = 0
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("logical_run_id") == logical_run_id:
                prior += 1
    if prior and not rerun_reason:
        raise RuntimeError(f"rerun reason required for {logical_run_id}")
    if prior >= 2:
        raise RuntimeError(f"rerun limit reached for {logical_run_id}")
    return prior + 1


def _append_attempt(ledger: Path, record: dict) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _result_count(
    path: Path,
    *,
    experiment_id: str,
    case_key: str,
    framework: str,
) -> int:
    if not path.exists():
        return 0
    return sum(
        d.get("experiment_id") == experiment_id
        and (d.get("case_id") or d.get("task_id")) == case_key
        and d.get("framework") == framework
        for d in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        type=Path,
        default=DEFAULT_TASK,
        help="A task JSON file, or a directory of task JSON files.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name for this benchmark session. Overrides OPENAI_MODEL from .env.",
    )
    parser.add_argument(
        "--experiment-id",
        default=None,
        help="Stable ID grouping all runs in this invocation. Generated when omitted.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Number of times to run each (task, framework) pair, to measure consistency.",
    )
    parser.add_argument(
        "--framework",
        choices=["all", *(name for name, _, _ in FRAMEWORKS)],
        default="all",
        help="Run all frameworks or one framework (used for a documented rerun).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Per-attempt subprocess timeout.",
    )
    parser.add_argument(
        "--rerun-reason",
        default=None,
        help="Required non-empty reason when repeating an existing logical run.",
    )
    parser.add_argument(
        "--required-keys",
        nargs="*",
        default=None,
        help="Keys expected in the JSON output, used for evaluation. "
        "Omit to skip the required-keys check (useful when sweeping "
        "tasks from more than one vertical at once).",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Load and list resolved cases without calling a model or writing results.",
    )
    args = parser.parse_args()

    experiment_id = args.experiment_id or f"exp-{uuid.uuid4().hex}"
    child_env = os.environ.copy()
    child_env["BENCHMARK_EXPERIMENT_ID"] = experiment_id
    if args.model:
        child_env["OPENAI_MODEL"] = args.model

    configured_model = child_env.get("OPENAI_MODEL", "from-.env")
    print(f"experiment_id={experiment_id} model={configured_model}")

    task_paths = _resolve_task_paths(args.task)
    gold_by_case = _load_gold(args.task)
    if not task_paths:
        print(f"no task files found at {args.task}")
        return

    if args.list_only:
        seen: set[str] = set()
        for task_path in task_paths:
            task = load_task(task_path)
            case_key = task.case_id or task.task_id
            if case_key in seen:
                raise SystemExit(f"duplicate case identity: {case_key}")
            seen.add(case_key)
            print(
                f"CASE {case_key} task={task.task_id} vertical={task.vertical} "
                f"allowed_tools={len(task.allowed_tools or [])}"
            )
        print(f"LIST_ONLY_OK cases={len(seen)} model_calls=0 result_writes=0")
        return

    tasks_by_key = {}
    frameworks = (
        FRAMEWORKS
        if args.framework == "all"
        else [row for row in FRAMEWORKS if row[0] == args.framework]
    )

    # (vertical, case identity, framework) once per run, in run order.
    run_records: list[tuple[str, str, str]] = []
    baseline_counts: dict[tuple[str, str, str], int] = {}
    for task_path in task_paths:
        task = load_task(task_path)
        vertical = task.vertical
        task_id = task.task_id
        case_key = task.case_id or task_id
        tasks_by_key[(vertical, case_key)] = task

        print(f"\n=== Case {case_key} / Task {task_id} ({task_path.name}) ===")
        for name, python_bin, script in frameworks:
            if not python_bin.exists():
                print(f"skipping {name}: {python_bin} not found (run scripts/setup_envs.sh)")
                continue

            baseline_counts[(vertical, case_key, name)] = _result_count(
                default_result_path(vertical),
                experiment_id=experiment_id,
                case_key=case_key,
                framework=name,
            )
            for rep in range(args.repeats):
                print(f"--- Running {name} (repeat {rep + 1}/{args.repeats}) ---")
                logical_run_id = (
                    f"{experiment_id}:{case_key}:{name}:repeat-{rep + 1}"
                )
                attempt = _next_attempt(
                    ATTEMPT_LEDGER,
                    logical_run_id,
                    args.rerun_reason,
                )
                started_at = datetime.now(timezone.utc).isoformat()
                try:
                    completed = subprocess.run(
                        [str(python_bin), str(script), "--task", str(task_path)],
                        cwd=ROOT,
                        check=False,
                        env=child_env,
                        timeout=args.timeout_seconds,
                    )
                    status = "completed" if completed.returncode == 0 else "process_error"
                    returncode = completed.returncode
                except subprocess.TimeoutExpired:
                    status = "timeout"
                    returncode = None
                _append_attempt(
                    ATTEMPT_LEDGER,
                    {
                        "logical_run_id": logical_run_id,
                        "experiment_id": experiment_id,
                        "case_id": case_key,
                        "task_id": task_id,
                        "framework": name,
                        "repeat": rep + 1,
                        "attempt": attempt,
                        "rerun_reason": args.rerun_reason,
                        "timeout_seconds": args.timeout_seconds,
                        "started_at": started_at,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "status": status,
                        "returncode": returncode,
                    },
                )
                if status != "completed":
                    raise RuntimeError(f"{logical_run_id} ended with {status}")
                run_records.append((vertical, case_key, name))

    print("\n--- Summary ---")
    by_vertical: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for vertical, case_key, name in run_records:
        by_vertical[vertical].append((case_key, name))

    failure_modes_by_framework: dict[str, Counter] = defaultdict(Counter)

    for vertical, records in by_vertical.items():
        results_path = default_result_path(vertical)
        if not results_path.exists():
            print(f"no results written to {results_path}")
            continue

        all_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        with open(results_path, "r", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                if d.get("experiment_id") != experiment_id:
                    continue
                result_case_key = d.get("case_id") or d["task_id"]
                all_by_key[(result_case_key, d["framework"])].append(d)

        key_counts = Counter(records)
        seen: set[tuple[str, str]] = set()
        for key in records:
            if key in seen:
                continue
            seen.add(key)

            case_key, name = key
            n = key_counts[key]
            session_runs = _require_session_runs(
                all_by_key[key][baseline_counts[(vertical, case_key, name)]:],
                expected=n,
                case_key=case_key,
                framework=name,
            )
            results_objs = [AgentRunResult(**d) for d in session_runs]
            task = tasks_by_key[(vertical, case_key)]
            evaluation = task.metadata.get("evaluation", {})
            required_keys = (
                args.required_keys
                if args.required_keys is not None
                else evaluation.get("required_keys")
            )
            metrics_list = [
                evaluate_result(
                    r,
                    required_keys=required_keys,
                    exact_values=evaluation.get("exact_values"),
                    one_sentence_fields=evaluation.get("one_sentence_fields"),
                )
                for r in results_objs
            ]
            core_metrics = []
            e5_metrics = []
            if case_key in gold_by_case:
                if task.task_id == "E5":
                    gold_record = gold_by_case[case_key]
                    e5_metrics = [
                        evaluate_agent_result(
                            r,
                            gold_record,
                            lambda: TauReplayEnv(
                                {
                                    **gold_record["gold"],
                                    "case_id": gold_record["case_id"],
                                }
                            ),
                        )
                        for r in results_objs
                    ]
                else:
                    core_metrics = [
                        evaluate_core_gold(r, gold_by_case[case_key])
                        for r in results_objs
                    ]

            success_rate = sum(m["success"] for m in metrics_list) / n
            json_valid_rate = sum(m["json_valid"] for m in metrics_list) / n
            schema_checked = [
                metric for metric in metrics_list
                if metric["output_schema_checked"]
            ]
            output_schema_field = ""
            if schema_checked:
                output_schema_rate = (
                    sum(metric["output_schema_valid"] for metric in schema_checked)
                    / len(schema_checked)
                )
                output_schema_field = (
                    f"output_schema_valid_rate={output_schema_rate:.0%} "
                )
            instruction_following_rate = (
                sum(m["instruction_following_score"] for m in metrics_list) / n
            )
            avg_latency = sum(r.latency_seconds for r in results_objs) / n
            failure_modes_by_framework[name].update(m["failure_mode"] for m in metrics_list)

            required_keys_field = ""
            if required_keys:
                req_rate = sum(m["required_keys_present"] for m in metrics_list) / n
                required_keys_field = f"required_keys_rate={req_rate:.0%} "
            core_score_field = ""
            supported_core = [
                metric for metric in core_metrics if metric["supported"]
            ]
            if supported_core:
                core_score = sum(metric["score"] for metric in supported_core) / len(
                    supported_core
                )
                core_score_field = f"core_gold_score={core_score:.0%} "
            if e5_metrics:
                e5_passes = sum(metric["verdict"] == "pass" for metric in e5_metrics)
                core_score_field = f"e5_pass_rate={e5_passes / len(e5_metrics):.0%} "

            print(
                f"{case_key:>18} {name:>18} (n={n}): success_rate={success_rate:.0%} "
                f"json_valid_rate={json_valid_rate:.0%} "
                f"{output_schema_field}"
                f"instruction_following_rate={instruction_following_rate:.0%} "
                f"{required_keys_field}"
                f"{core_score_field}"
                f"avg_latency={avg_latency:.2f}s"
            )

    print("\n--- Failure Modes ---")
    for name, counts in failure_modes_by_framework.items():
        breakdown = ", ".join(f"{mode}={count}" for mode, count in counts.most_common())
        print(f"{name:>18}: {breakdown}")


if __name__ == "__main__":
    main()
