#!/usr/bin/env python3
"""Validate owner-provided dataset specifications without approving them."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"draft_pending_approval", "approved"}


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise AssertionError(f"{path.name} must contain a JSON object")
    return value


def _validate_h2(document: dict) -> int:
    assert document.get("schema_version") == "1.0"
    assert document.get("status") in ALLOWED_STATUSES
    assert document.get("task_id") == "H2"
    assert document.get("source_field") == "prompt_id"
    assert set(document.get("target_values", [])) == {
        "emergency",
        "urgent",
        "routine",
        "self_care",
        "uncertain",
    }
    assert document.get("unmapped_policy") == "flag_for_manual_review"

    distribution = document["measured_distribution"]
    selected_count = distribution["theme_counts"]["emergency_referrals"]
    category_counts = distribution["emergency_referrals_physician_agreed_category"]
    assert sum(category_counts.values()) == selected_count
    assert document["extraction_rule"]["emergency"]["expected_count"] == category_counts[
        "emergent"
    ]
    assert document["extraction_rule"]["uncertain"]["expected_count"] == category_counts[
        "conditionally-emergent"
    ]
    assert {"easy", "medium", "hard"} <= set(document["difficulty_generation_rule"])
    return selected_count


def _validate_h4(document: dict) -> int:
    assert document.get("schema_version") == "1.0"
    assert document.get("status") in ALLOWED_STATUSES
    assert document.get("task_id") == "H4"
    assert document.get("source_field") == "encounter_id"
    assert document.get("unmapped_policy") == "flag_for_manual_review"
    assert {"symptoms", "history", "risks", "next_steps"} == set(
        document.get("extraction_rule", {})
    )
    assert document.get("empty_section_handling")
    assert document["split_mapping"]["status"] == "confirmed"
    assert document["split_mapping"]["total_cases"] == 207
    assert len(document["source_files_confirmed"]["note_and_dialogue_files"]) == 5
    assert {"easy", "medium", "hard"} <= set(document["difficulty_generation_rule"])
    return document["split_mapping"]["total_cases"]


def main() -> None:
    h2 = _load(ROOT / "mappings" / "h2_urgency_mapping.json")
    h4 = _load(ROOT / "evaluator_data" / "gold_answers" / "h4_extraction_spec.json")
    h2_candidates = _validate_h2(h2)
    h4_cases = _validate_h4(h4)
    print(
        "DATASET_SPECS_OK "
        f"h2_status={h2['status']} h2_candidates={h2_candidates} "
        f"h4_status={h4['status']} h4_cases={h4_cases}"
    )


if __name__ == "__main__":
    main()
