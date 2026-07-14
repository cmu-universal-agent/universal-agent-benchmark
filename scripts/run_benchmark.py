#!/usr/bin/env python3
"""Run the same benchmark task through all three framework adapters.

Each framework runs in its own virtual environment via subprocess, writes its
AgentRunResult to results/metrics/<vertical>_results.jsonl, then this script
prints a short evaluation summary.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.evaluator import evaluate_result
from adapter.result_writer import default_result_path
from adapter.schemas import AgentRunResult

DEFAULT_TASK = ROOT / "verticals" / "smoke_test" / "task_001.json"

FRAMEWORKS = [
    (
        "openai_agents_sdk",
        ROOT / ".venv-openai" / "bin" / "python",
        ROOT / "frameworks" / "openai_agents_sdk" / "run.py",
    ),
    (
        "langgraph",
        ROOT / ".venv-langgraph" / "bin" / "python",
        ROOT / "frameworks" / "langgraph_agent" / "run.py",
    ),
    (
        "crewai",
        ROOT / ".venv-crewai" / "bin" / "python",
        ROOT / "frameworks" / "crewai_agent" / "run.py",
    ),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, default=DEFAULT_TASK)
    parser.add_argument(
        "--required-keys",
        nargs="*",
        default=["task_id", "answer", "safety_note"],
        help="Keys expected in the JSON output, used for evaluation.",
    )
    args = parser.parse_args()

    with open(args.task, "r", encoding="utf-8") as f:
        vertical = json.load(f)["vertical"]

    ran = []
    for name, python_bin, script in FRAMEWORKS:
        if not python_bin.exists():
            print(f"skipping {name}: {python_bin} not found (run scripts/setup_envs.sh)")
            continue

        print(f"\n--- Running {name} ---")
        subprocess.run(
            [str(python_bin), str(script), "--task", str(args.task)],
            cwd=ROOT,
            check=False,
        )
        ran.append(name)

    print("\n--- Summary ---")
    results_path = default_result_path(vertical)
    if not results_path.exists():
        print(f"no results written to {results_path}")
        return

    with open(results_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines[-len(ran):]:
        result = AgentRunResult(**json.loads(line))
        metrics = evaluate_result(result, required_keys=args.required_keys)
        print(
            f"{metrics['framework']:>18}: success={metrics['success']} "
            f"json_valid={metrics['json_valid']} "
            f"required_keys_present={metrics['required_keys_present']} "
            f"latency={metrics['latency_seconds']:.2f}s"
        )


if __name__ == "__main__":
    main()
