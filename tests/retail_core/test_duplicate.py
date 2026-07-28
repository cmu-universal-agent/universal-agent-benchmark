import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import DUPLICATE_ACTION

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestDuplicate(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID, reset_id="reset-duplicate")

    def test_repeated_read_call_is_idempotent_and_both_appear_in_trace(self) -> None:
        first = self.env.call_tool("get_order_details", {"order_id": "O5001"})
        second = self.env.call_tool("get_order_details", {"order_id": "O5001"})
        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.data, second.data)
        self.assertEqual(len(self.env.get_trace()), 2)

    def test_duplicate_mutation_is_hard_error_and_second_call_does_not_change_state(self) -> None:
        arguments = {
            "order_id": "O5001",
            "item_ids": ["P1001-BLK"],
            "payment_method_id": "credit_card_100",
        }
        first = self.env.call_tool("return_delivered_order_items", arguments)
        self.assertTrue(first.ok)
        self.assertTrue(first.state_changed)
        state_after_first = self.env.get_final_state()

        second = self.env.call_tool("return_delivered_order_items", arguments)
        self.assertFalse(second.ok)
        self.assertEqual(second.error_type, DUPLICATE_ACTION)
        self.assertFalse(second.state_changed)

        state_after_second = self.env.get_final_state()
        self.assertEqual(state_after_first["state_sha256"], state_after_second["state_sha256"])
        self.assertEqual(state_after_first["mutation_count"], 1)
        self.assertEqual(state_after_second["mutation_count"], 1)

        trace = self.env.get_trace()
        self.assertEqual(len(trace), 2)
        self.assertEqual(trace[0]["outcome"], "success")
        self.assertEqual(trace[1]["outcome"], "error")
        self.assertEqual(trace[1]["error"]["error_type"], DUPLICATE_ACTION)
        self.assertFalse(trace[1]["error"]["retryable"])


if __name__ == "__main__":
    unittest.main()
