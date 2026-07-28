import json
import unittest

from adapter.evaluator import evaluate_result
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


if __name__ == "__main__":
    unittest.main()
