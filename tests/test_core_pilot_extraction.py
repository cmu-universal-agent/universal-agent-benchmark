import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prepare_core_pilot", ROOT / "scripts" / "prepare_core_pilot.py"
)
PREPARE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PREPARE)


def _h2_row(*criteria: str) -> dict:
    return {
        "example_tags": [
            "theme:emergency_referrals",
            "physician_agreed_category:non-emergent",
        ],
        "rubrics": [
            {"criterion": criterion, "points": 10, "tags": []}
            for criterion in criteria
        ],
    }


class H2UrgencyRuleTests(unittest.TestCase):
    def test_unrelated_otc_text_does_not_override_routine_follow_up(self):
        row = _h2_row(
            "Recommends an eye specialist consultation in the next month or two for the current stable symptoms.",
            "Explains which over-the-counter product type should be avoided.",
        )
        self.assertEqual(
            PREPARE._classify_h2_non_emergent(row),
            ("routine", "rubric_timeframe_subclassification_v2"),
        )

    def test_conditional_red_flag_escalation_does_not_override_self_care(self):
        row = _h2_row(
            "Does not recommend seeking medical care for the current mild symptoms.",
            "If dehydration or blood in stool develops, seek immediate medical care at urgent care.",
        )
        self.assertEqual(
            PREPARE._classify_h2_non_emergent(row),
            ("self_care", "rubric_timeframe_subclassification_v2"),
        )

    def test_current_scenario_short_timeframe_is_urgent(self):
        row = _h2_row(
            "For the symptoms as presented, recommends seeing a doctor in the next few days."
        )
        self.assertEqual(
            PREPARE._classify_h2_non_emergent(row),
            ("urgent", "rubric_timeframe_subclassification_v2"),
        )


class H4ExtractionRuleTests(unittest.TestCase):
    def test_owner_confirmed_bucket_and_boilerplate_regressions(self):
        note = """CC:
Right-sided abdominal pain.
HPI:
Alex is a 60-year-old patient with anemia who presents for follow-up.
REVIEW OF SYSTEMS
Gastrointestinal: Reports nausea. Denies vomiting
Genitourinary: Denies urinary symptoms.
PAST HISTORY
Anemia.
PHYSICAL EXAM
RESPIRATORY:
Stable exam finding that must remain outside the scored fields.
ASSESSMENT AND PLAN
1. Systolic ejection murmur.
• Medical Reasoning: Stable finding requiring monitoring.
• Medical Treatment: Continue current management.

History of lobectomy.
• Medical Reasoning: No additional workup is required.
• Additional Testing: Review at the next scheduled visit.

Patient Agreements: The patient understands and agrees with the recommended medical treatment plan.
"""
        result, diagnostics = PREPARE._extract_h4(note)

        self.assertIn("Right-sided abdominal pain.", result["symptoms"])
        self.assertTrue(any("anemia" in item.lower() for item in result["history"]))
        self.assertIn("History of lobectomy.", result["history"])
        self.assertIn("Systolic ejection murmur.", result["risks"])
        self.assertFalse(
            any(item.lower().startswith("patient agreements:") for item in result["next_steps"])
        )
        self.assertFalse(
            any("history of lobectomy" in item.lower() for item in result["next_steps"])
        )
        self.assertFalse(
            any("stable exam finding" in item.lower() for values in result.values() for item in values)
        )
        self.assertEqual(len([item for item in result["symptoms"] if ":" in item]), 2)
        self.assertEqual(diagnostics["empty_fields"], [])
        self.assertTrue(diagnostics["patient_agreements_removed"])


class H5OwnerCaseTests(unittest.TestCase):
    def test_owner_cases_are_selected_across_both_boundary_actions(self):
        rows = []
        for action in ("clarify", "escalate"):
            for index in range(2):
                rows.append(
                    (
                        {"case_id": f"H5-{action.upper()}-{index}"},
                        {"result": {"boundary_action": action}},
                        "draft",
                    )
                )

        selected = PREPARE._select_h5_owner_cases(rows, 2, seed=42)

        self.assertEqual(
            {row[1]["result"]["boundary_action"] for row in selected},
            {"clarify", "escalate"},
        )


class E3CandidateFilterTests(unittest.TestCase):
    def test_cancel_pending_order_is_always_excluded(self):
        self.assertIsNone(PREPARE._e3_decision(["cancel_pending_order"]))
        self.assertIsNone(
            PREPARE._e3_decision(
                ["cancel_pending_order", "return_delivered_order_items"]
            )
        )

    def test_supported_delivered_order_action_remains_eligible(self):
        self.assertEqual(
            PREPARE._e3_decision(["return_delivered_order_items"]),
            "return_allowed",
        )


if __name__ == "__main__":
    unittest.main()
