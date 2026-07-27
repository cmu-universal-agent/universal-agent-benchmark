import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestFinalState(unittest.TestCase):
    def test_final_state_matches_expected_state_for_a_scripted_success_sequence(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(CASE_ID)

        env.call_tool("get_order", {"order_id": "O5001"})  # read, no effect on final state
        result = env.call_tool("refund_order", {"order_id": "O5001", "reason": "defective"})
        self.assertTrue(result.ok)

        final_state = env.get_final_state()
        order = final_state["orders"]["O5001"]
        self.assertEqual(order["status"], "refunded")
        self.assertEqual(order["refunded_amount"], 25.99)

        # untouched records are unaffected by the scripted sequence
        self.assertEqual(final_state["orders"]["O5002"]["status"], "delivered")
        self.assertEqual(final_state["users"]["U100"]["name"], "Alice Chen")

    def test_failed_operations_do_not_alter_final_state(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(CASE_ID)
        before = env.get_final_state()

        env.call_tool("refund_order", {"order_id": "O9999", "reason": "defective"})  # disallowed_action
        env.call_tool("refund_order", {"order_id": "O5001"})  # invalid_arguments

        after = env.get_final_state()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
