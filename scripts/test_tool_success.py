#!/usr/bin/env python3
"""Force a successful tool call and inspect the normalized adapter result.

Run this once inside each framework virtual environment. It makes one model
call per selected vertical and does not append the result to benchmark metrics.
"""

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.schemas import BenchmarkTask

RUN_MODULES = {
    "openai_agents_sdk": "frameworks.openai_agents_sdk.run",
    "langgraph": "frameworks.langgraph_agent.run",
    "crewai": "frameworks.crewai_agent.run",
}

SCENARIOS = {
    "medical_diagnostic": BenchmarkTask(
        task_id="TOOLSUCCESS-MED",
        vertical="medical_diagnostic",
        prompt=(
            'You must call search_literature with pubmed_id="21550158" before answering. '
            "Return exactly one JSON object with keys task_id and status. "
            'task_id must be "TOOLSUCCESS-MED" and status must be "completed".'
        ),
        metadata={"prompt_version": "tool_success_v1"},
    ),
    "ecommerce_trend_research": BenchmarkTask(
        task_id="TOOLSUCCESS-ECOM",
        vertical="ecommerce_trend_research",
        prompt=(
            'You must call get_review_history with parent_asin="B07KTB8PHS" before answering. '
            "Return exactly one JSON object with keys task_id and status. "
            'task_id must be "TOOLSUCCESS-ECOM" and status must be "completed".'
        ),
        metadata={"prompt_version": "tool_success_v1"},
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", required=True, choices=RUN_MODULES)
    parser.add_argument("--vertical", choices=SCENARIOS, default="medical_diagnostic")
    args = parser.parse_args()

    run_module = importlib.import_module(RUN_MODULES[args.framework])
    result = run_module.run_task(SCENARIOS[args.vertical])
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))

    if not result.success:
        raise SystemExit("FAIL: adapter returned success=False")
    if not result.tool_calls:
        raise SystemExit("FAIL: no normalized tool call was recorded")
    if result.tool_calls[0].get("outcome") != "success":
        raise SystemExit("FAIL: recorded tool call did not succeed")
    print("PASS: successful tool call and normalized trace were recorded")


if __name__ == "__main__":
    main()
