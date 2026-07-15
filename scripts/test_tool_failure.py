#!/usr/bin/env python3
"""Simulated tool-failure test.

Forces a framework to call a mock tool that raises an exception, and
reports whether the framework/run_task handled it gracefully (the agent
recovered and still returned a best-effort JSON answer, or run_task cleanly
caught the exception and returned success=False) rather than the whole
process crashing. Must be run once per framework, inside that framework's
venv, since the frameworks are not co-installed in one environment:

    source .venv-openai/bin/activate && python scripts/test_tool_failure.py --framework openai_agents_sdk && deactivate
    source .venv-langgraph/bin/activate && python scripts/test_tool_failure.py --framework langgraph && deactivate
    source .venv-crewai/bin/activate && python scripts/test_tool_failure.py --framework crewai && deactivate
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
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

RUN_MODULES = {
    "openai_agents_sdk": "frameworks.openai_agents_sdk.run",
    "langgraph": "frameworks.langgraph_agent.run",
    "crewai": "frameworks.crewai_agent.run",
}

SCENARIOS = {
    "medical_diagnostic": {
        "tools_module": medical_tools,
        "prompt": (
            'You must call the search_literature tool with pubmed_id="26370095" '
            "to retrieve the research abstract before answering. "
            "If the tool call fails, note that in your rationale and still give "
            "your best-effort answer rather than refusing to respond. "
            "Then answer this question: Are financial incentives cost-effective "
            "to support smoking cessation during pregnancy? "
            "Return exactly one JSON object with keys: task_id, answer, "
            "rationale, confidence, safety_note. task_id must be "
            '"TOOLFAIL-MED". answer must be one of yes/no/maybe. '
            'safety_note must be exactly "no real clinical decision made".'
        ),
        "task_id": "TOOLFAIL-MED",
    },
    "ecommerce_trend_research": {
        "tools_module": ecommerce_tools,
        "prompt": (
            'You must call the get_review_history tool with parent_asin="B07GC48H1H" '
            "to retrieve the yearly review data before answering. "
            "If the tool call fails, note that in your rationale and still give "
            "your best-effort answer rather than refusing to respond. "
            "Then synthesize the trend as best you can. "
            "Return exactly one JSON object with keys: task_id, trend_direction, "
            "sentiment_direction, trend_summary, confidence, safety_note. "
            'task_id must be "TOOLFAIL-ECOM". trend_direction must be one of '
            "rising/declining/stable. sentiment_direction must be one of "
            "improving/declining/stable. safety_note must be exactly "
            '"no real purchasing decision made".'
        ),
        "task_id": "TOOLFAIL-ECOM",
    },
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", required=True, choices=RUN_MODULES.keys())
    parser.add_argument(
        "--vertical", choices=SCENARIOS.keys(), default=None, help="Default: run both."
    )
    args = parser.parse_args()

    run_module = importlib.import_module(RUN_MODULES[args.framework])
    verticals = [args.vertical] if args.vertical else list(SCENARIOS.keys())

    for vertical in verticals:
        scenario = SCENARIOS[vertical]
        scenario["tools_module"].set_simulate_failure(True)
        task = BenchmarkTask(
            task_id=scenario["task_id"], vertical=vertical, prompt=scenario["prompt"]
        )
        print(f"--- {args.framework} / {vertical} ---")
        try:
            result = run_module.run_task(task)
            print(f"run_task returned without raising (expected)")
            print(f"success={result.success} tool_call_count={result.tool_call_count}")
            print(f"error={result.error}")
            print(f"final_output={result.final_output!r}")
            print(f"model={result.model_name} run_id={result.run_id}")
            print(f"tool_calls={json.dumps(result.tool_calls, ensure_ascii=False)}")
        except Exception as exc:
            print(f"CRASHED -- run_task raised instead of catching: {type(exc).__name__}: {exc}")
        finally:
            scenario["tools_module"].set_simulate_failure(False)
        print()


if __name__ == "__main__":
    main()
