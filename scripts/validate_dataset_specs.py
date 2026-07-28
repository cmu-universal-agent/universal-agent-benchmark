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
    assert document.get("rule_version") == "h2-urgency-v2"
    assert document.get("urgency_mapping_status") == "approved"
    assert document.get("gold_generation_status") == "complete"
    assert document.get("remaining_approval_scope") == "none_for_h2_gold"
    assert document.get("difficulty_rule_disposition") == (
        "provisional_retained_revisit_later"
    )
    assert document.get("difficulty_project_decision", {}).get("decided_by") == (
        "Jessica"
    )
    assert document["owner_feedback"]["difficulty_feedback"][
        "threshold_recommendation"
    ] is None
    assert document.get("owner_feedback", {}).get("reviewed_by") == "Chloe"
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
    lower_rule = document["extraction_rule"]["urgent_routine_self_care_subclassification"]
    assert lower_rule.get("criterion_scope_rule")
    assert lower_rule.get("precedence_rule")
    assert document["owner_feedback"]["confirmed_review_cases"] == {
        "H2-REVIEW-003": "urgent",
        "H2-REVIEW-004": "routine",
        "H2-REVIEW-005": "routine",
        "H2-REVIEW-008": "self_care",
    }
    measured_difficulty = document["difficulty_generation_rule"][
        "measured_subset_distribution"
    ]
    assert measured_difficulty["records"] == selected_count
    assert sum(
        measured_difficulty["current_rule_usable_category_distribution"].values()
    ) == selected_count - category_counts["no_category_tag"]
    assert {"easy", "medium", "hard"} <= set(document["difficulty_generation_rule"])
    return selected_count


def _validate_h4(document: dict) -> int:
    assert document.get("schema_version") == "1.0"
    assert document.get("status") in ALLOWED_STATUSES
    assert document.get("rule_version") == "h4-extraction-v2"
    assert document.get("owner_feedback", {}).get("reviewed_by") == "Chloe"
    assert document.get("task_id") == "H4"
    assert document.get("source_field") == "encounter_id"
    assert document.get("unmapped_policy") == "flag_for_manual_review"
    assert {"symptoms", "history", "risks", "next_steps"} == set(
        document.get("extraction_rule", {})
    )
    assert document.get("empty_section_handling")
    abbreviated = document["abbreviated_header_alias_table"]
    assert {"CC:", "HPI:", "MSK:", "RESPIRATORY:", "OTC:"} <= set(abbreviated)
    assert document.get("boilerplate_stoplist", {}).get("fix")
    assert document.get("numbered_problem_title_handling", {}).get("fix")
    assert document["extraction_rule"]["history"].get("supplemental_source")
    assert document["split_mapping"]["status"] == "confirmed"
    assert document["split_mapping"]["total_cases"] == 207
    assert len(document["source_files_confirmed"]["note_and_dialogue_files"]) == 5
    assert {"easy", "medium", "hard"} <= set(document["difficulty_generation_rule"])
    return document["split_mapping"]["total_cases"]


def _validate_h5(document: dict) -> int:
    assert document.get("schema_version") == "1.0"
    assert document.get("status") in ALLOWED_STATUSES
    assert document.get("rule_version") == "h5-manual-cases-v1-draft"
    assert document.get("task_id") == "H5"
    feedback = document.get("owner_feedback", {})
    assert feedback.get("authored_by") == "Chloe"
    assert feedback.get("review_status") == "not_reviewed"
    supplied = feedback.get("cases_supplied", {})
    assert supplied == {"clarify": 2, "escalate": 2}
    requirements = document.get("rubric_requirements", {})
    assert set(requirements.get("required_boundary_actions", [])) == {
        "clarify",
        "escalate",
    }
    assert requirements.get("positive_and_negative_criteria_required") is True
    assert document.get("storage_rule")
    assert document.get("pilot_selection_rule")
    return sum(supplied.values())


def _validate_e3(document: dict) -> str:
    assert document.get("schema_version") == "1.0"
    assert document.get("status") == "approved"
    assert document.get("rule_version") == "e3-candidate-filter-v1"
    assert document.get("task_id") == "E3"
    assert document.get("owner_feedback", {}).get("reviewed_by") == "Chloe"
    assert document.get("owner_feedback", {}).get("decision") == (
        "exclude_cancel_pending_order"
    )
    assert document.get("excluded_action") == "cancel_pending_order"
    assert document.get("prohibited_mapping") == (
        "cancel_pending_order -> refund_allowed"
    )
    assert document.get("unmapped_policy") == "reject_from_candidate_pool"
    return document["status"]


def main() -> None:
    h2 = _load(ROOT / "mappings" / "h2_urgency_mapping.json")
    h4 = _load(ROOT / "evaluator_data" / "gold_answers" / "h4_extraction_spec.json")
    h5 = _load(ROOT / "evaluator_data" / "rubrics" / "h5_manual_case_spec.json")
    e3 = _load(ROOT / "mappings" / "e3_candidate_filter.json")
    h2_candidates = _validate_h2(h2)
    h4_cases = _validate_h4(h4)
    h5_cases = _validate_h5(h5)
    e3_status = _validate_e3(e3)
    print(
        "DATASET_SPECS_OK "
        f"h2_status={h2['status']} "
        f"h2_mapping_status={h2['urgency_mapping_status']} "
        f"h2_gold_status={h2['gold_generation_status']} "
        f"h2_difficulty={h2['difficulty_rule_disposition']} "
        f"h2_candidates={h2_candidates} "
        f"h4_status={h4['status']} h4_cases={h4_cases} "
        f"h5_status={h5['status']} h5_owner_cases={h5_cases} "
        f"e3_status={e3_status}"
    )


if __name__ == "__main__":
    main()
