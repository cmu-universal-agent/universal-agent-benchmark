#!/usr/bin/env python3
"""Report hallucination-risk metrics across all frameworks.

Uses the latest result per (task_id, framework, model) in results/metrics/*.jsonl,
matched against each task's ground truth in verticals/<vertical>/task_*.json.
The headline metric is "confidently wrong": answers stated with high
confidence that don't match ground truth -- the failure mode CLAUDE.md's
safety constraints most want penalized, since it's the opposite of "safe
refusal and structured reasoning."
"""

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.evaluator import evaluate_hallucination_risk
from adapter.ground_truth import GROUND_TRUTH_CONFIG, load_ground_truth
from adapter.result_writer import load_latest_results, result_models
from adapter.schemas import AgentRunResult


def main():
    for vertical, config in GROUND_TRUTH_CONFIG.items():
        ground_truth = load_ground_truth(vertical)
        for model_name in result_models(vertical):
            results = load_latest_results(vertical, model_name=model_name)
            by_framework: dict[str, list[dict]] = defaultdict(list)
            for (task_id, framework), r in results.items():
                if task_id not in ground_truth:
                    continue
                result = AgentRunResult(**r)
                metrics = evaluate_hallucination_risk(
                    result, ground_truth[task_id], config["answer_key"]
                )
                by_framework[framework].append(metrics)

            print(f"=== {vertical} / model={model_name} ===")
            for framework, rows in sorted(by_framework.items()):
                total = len(rows)
                correct = sum(1 for r in rows if r["answer_correct"])
                confidently_wrong = [r for r in rows if r["confidently_wrong"]]
                print(
                    f"{framework:>18}: accuracy={correct}/{total} "
                    f"confidently_wrong={len(confidently_wrong)}/{total}"
                )
                for r in confidently_wrong:
                    print(
                        f"    {r['task_id']}: said {r['stated_answer']!r} "
                        f"(confidence={r['stated_confidence']!r}) but ground truth is "
                        f"{r['ground_truth']!r}"
                    )
            print()


if __name__ == "__main__":
    main()
