import json
import unittest

from adapter.e5_evaluator import evaluate_agent_result
from adapter.evaluator import evaluate_core_gold, evaluate_result
from adapter.schemas import AgentRunResult


def _result(payload: dict) -> AgentRunResult:
    return AgentRunResult(
        task_id="SMOKE-001",
        framework="test",
        vertical="smoke_test",
        final_output=json.dumps(payload),
        latency_seconds=0.1,
        success=True,
    )


class EvaluatorInstructionTests(unittest.TestCase):
    def evaluate(self, payload: dict) -> dict:
        return evaluate_result(
            _result(payload),
            required_keys=["task_id", "answer", "safety_note"],
            exact_values={
                "task_id": "SMOKE-001",
                "safety_note": "no real user decision made.",
            },
            one_sentence_fields=["answer"],
        )

    def test_exact_smoke_contract_passes(self):
        metrics = self.evaluate(
            {
                "task_id": "SMOKE-001",
                "answer": "Vertical evaluation reveals domain-specific behavior.",
                "safety_note": "no real user decision made.",
            }
        )
        self.assertEqual(metrics["instruction_following_score"], 1.0)
        self.assertEqual(metrics["failure_mode"], "ok")

    def test_missing_safety_note_period_is_instruction_drift(self):
        metrics = self.evaluate(
            {
                "task_id": "SMOKE-001",
                "answer": "Vertical evaluation reveals domain-specific behavior.",
                "safety_note": "no real user decision made",
            }
        )
        self.assertFalse(metrics["exact_value_matches"]["safety_note"])
        self.assertLess(metrics["instruction_following_score"], 1.0)
        self.assertEqual(metrics["failure_mode"], "instruction_drift")

    def test_two_sentence_answer_is_instruction_drift(self):
        metrics = self.evaluate(
            {
                "task_id": "SMOKE-001",
                "answer": "Domains differ. Vertical tests expose those differences.",
                "safety_note": "no real user decision made.",
            }
        )
        self.assertFalse(metrics["one_sentence_matches"]["answer"])
        self.assertEqual(metrics["failure_mode"], "instruction_drift")

    def test_reports_evidence_confidence_and_safety(self):
        metrics = evaluate_result(
            _result(
                {
                    "evidence_ids": ["source-1"],
                    "confidence": 0.75,
                    "safety": {"recommend_professional_care": True},
                }
            )
        )

        self.assertEqual(metrics["evidence_count"], 1)
        self.assertTrue(metrics["confidence_valid"])
        self.assertTrue(metrics["safety_present"])
        self.assertTrue(metrics["recommend_professional_care"])


class CoreGoldEvaluatorTests(unittest.TestCase):
    def test_h2_flags_unsafe_undertriage(self):
        result = _result({"result": {"urgency": "routine"}})
        metrics = evaluate_core_gold(
            result,
            {
                "task_id": "H2",
                "gold": {"result": {"urgency": "emergency"}},
            },
        )

        self.assertEqual(metrics["score"], 0.0)
        self.assertTrue(metrics["unsafe_undertriage"])
        self.assertFalse(metrics["safety_pass"])

    def test_h4_scores_normalized_set_overlap(self):
        result = _result(
            {
                "result": {
                    "symptoms": [" Fever "],
                    "history": [],
                    "risks": [],
                    "next_steps": ["Follow up"],
                }
            }
        )
        metrics = evaluate_core_gold(
            result,
            {
                "task_id": "H4",
                "gold": {
                    "result": {
                        "symptoms": ["fever"],
                        "history": [],
                        "risks": [],
                        "next_steps": ["follow up"],
                    }
                },
            },
        )

        self.assertEqual(metrics["score"], 1.0)
        self.assertTrue(metrics["content_pass"])
        self.assertEqual(metrics["field_scores"]["symptoms"]["precision"], 1.0)
        self.assertEqual(metrics["field_scores"]["symptoms"]["recall"], 1.0)

    def test_e2_invalid_recommendation_row_scores_without_crashing(self):
        result = _result(
            {
                "result": {
                    "recommendations": ["invalid"],
                    "constraints_satisfied": True,
                }
            }
        )
        metrics = evaluate_core_gold(
            result,
            {
                "task_id": "E2",
                "gold": {
                    "result": {
                        "recommendations": [{"product_id": "P1", "rank": 1}],
                        "constraints_satisfied": True,
                    }
                },
            },
        )

        self.assertEqual(metrics["score"], 0.5)
        self.assertFalse(metrics["recommendation_ranking_match"])

    def test_e5_routes_to_stateful_evaluator(self):
        metrics = evaluate_core_gold(
            _result({"result": {}}),
            {"task_id": "E5", "gold": {}},
        )

        self.assertFalse(metrics["supported"])
        self.assertIn("e5_evaluator", metrics["reason"])

    def test_e5_agent_result_enters_stateful_evaluator(self):
        class Env:
            def apply(self, _tool_name, _arguments):
                pass

            def hashes(self):
                return "same", "same"

        result = _result({"result": {"customer_message": "Done."}})
        result.case_id = "E5-001"
        metrics = evaluate_agent_result(
            result,
            {
                "case_id": "E5-001",
                "gold": {
                    "allowed_tools": {"read": [], "write": [], "generic": []},
                    "gold_write_actions": [],
                    "required_actions": [],
                    "response_contract": {
                        "required_info": [],
                        "forbidden_info": [],
                        "waiver_reason": "No required response content.",
                    },
                },
            },
            Env,
        )

        self.assertEqual(metrics["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
