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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.evaluator import evaluate_result
from adapter.result_writer import default_result_path
from adapter.schemas import AgentRunResult
from adapter.task_loader import load_task

DEFAULT_TASK = ROOT / "verticals" / "smoke_test" / "task_001.json"


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
        "--required-keys",
        nargs="*",
        default=None,
        help="Keys expected in the JSON output, used for evaluation. "
        "Omit to skip the required-keys check (useful when sweeping "
        "tasks from more than one vertical at once).",
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
    if not task_paths:
        print(f"no task files found at {args.task}")
        return

    # (vertical, task_id, framework) once per run, in the order they ran
    run_records: list[tuple[str, str, str]] = []
    for task_path in task_paths:
        task = load_task(task_path)
        vertical = task.vertical
        task_id = task.task_id

        print(f"\n=== Task {task_id} ({task_path.name}) ===")
        for name, python_bin, script in FRAMEWORKS:
            if not python_bin.exists():
                print(f"skipping {name}: {python_bin} not found (run scripts/setup_envs.sh)")
                continue

            for rep in range(args.repeats):
                print(f"--- Running {name} (repeat {rep + 1}/{args.repeats}) ---")
                subprocess.run(
                    [str(python_bin), str(script), "--task", str(task_path)],
                    cwd=ROOT,
                    check=False,
                    env=child_env,
                )
                run_records.append((vertical, task_id, name))

    print("\n--- Summary ---")
    by_vertical: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for vertical, task_id, name in run_records:
        by_vertical[vertical].append((task_id, name))

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
                all_by_key[(d["task_id"], d["framework"])].append(d)

        key_counts = Counter(records)
        seen: set[tuple[str, str]] = set()
        for key in records:
            if key in seen:
                continue
            seen.add(key)

            task_id, name = key
            n = key_counts[key]
            # this session's runs are the most recently appended n entries
            session_runs = all_by_key[key][-n:]
            results_objs = [AgentRunResult(**d) for d in session_runs]
            metrics_list = [
                evaluate_result(r, required_keys=args.required_keys) for r in results_objs
            ]

            success_rate = sum(m["success"] for m in metrics_list) / n
            json_valid_rate = sum(m["json_valid"] for m in metrics_list) / n
            instruction_following_rate = (
                sum(m["instruction_following_score"] for m in metrics_list) / n
            )
            avg_latency = sum(r.latency_seconds for r in results_objs) / n
            failure_modes_by_framework[name].update(m["failure_mode"] for m in metrics_list)

            required_keys_field = ""
            if args.required_keys:
                req_rate = sum(m["required_keys_present"] for m in metrics_list) / n
                required_keys_field = f"required_keys_rate={req_rate:.0%} "

            print(
                f"{task_id:>10} {name:>18} (n={n}): success_rate={success_rate:.0%} "
                f"json_valid_rate={json_valid_rate:.0%} "
                f"instruction_following_rate={instruction_following_rate:.0%} "
                f"{required_keys_field}"
                f"avg_latency={avg_latency:.2f}s"
            )

    print("\n--- Failure Modes ---")
    for name, counts in failure_modes_by_framework.items():
        breakdown = ", ".join(f"{mode}={count}" for mode, count in counts.most_common())
        print(f"{name:>18}: {breakdown}")


if __name__ == "__main__":
    main()
