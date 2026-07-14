#!/usr/bin/env python3
"""Report medical-vertical safety-constraint checks across all frameworks.

Checks CLAUDE.md's Safety Constraints for the Medical Diagnostic Assistant
vertical: the exact safety disclaimer is present, no directive/prescriptive
clinical language leaked into the rationale, and escalation/referral
language shows up when the model itself answers "maybe". Uses the latest
result per (task_id, framework) in results/metrics/medical_diagnostic_results.jsonl.
"""

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.evaluator import evaluate_medical_safety
from adapter.ground_truth import task_ids as load_task_ids
from adapter.result_writer import load_latest_results
from adapter.schemas import AgentRunResult

VERTICAL = "medical_diagnostic"


def main():
    valid_task_ids = load_task_ids(VERTICAL)
    latest = load_latest_results(VERTICAL)

    by_framework: dict[str, list[dict]] = defaultdict(list)
    for (task_id, framework), r in latest.items():
        if task_id not in valid_task_ids:
            continue
        result = AgentRunResult(**r)
        by_framework[framework].append(evaluate_medical_safety(result))

    for framework, rows in sorted(by_framework.items()):
        total = len(rows)
        safe = sum(1 for r in rows if r["medical_safety_ok"])
        bad_disclaimer = [r for r in rows if not r["safety_note_exact_match"]]
        risky = [r for r in rows if r["risky_phrases_found"]]
        missed_escalation = [
            r for r in rows if r["escalation_expected"] and not r["escalation_language_present"]
        ]
        print(f"{framework:>18}: medical_safety_ok={safe}/{total}")
        for r in bad_disclaimer:
            print(f"    {r['task_id']}: safety_note mismatch -> {r['safety_note']!r}")
        for r in risky:
            print(f"    {r['task_id']}: risky phrases found -> {r['risky_phrases_found']}")
        for r in missed_escalation:
            print(f"    {r['task_id']}: answered 'maybe' but no escalation/referral language")


if __name__ == "__main__":
    main()
