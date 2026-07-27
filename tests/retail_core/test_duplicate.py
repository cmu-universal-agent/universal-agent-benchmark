import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import DUPLICATE_MUTATION

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestDuplicate(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID)

    def test_repeated_read_call_is_idempotent_and_both_appear_in_trace(self) -> None:
        first = self.env.call_tool("get_order", {"order_id": "O5001"})
        second = self.env.call_tool("get_order", {"order_id": "O5001"})
        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.data, second.data)
        self.assertEqual(len(self.env.get_trace()), 2)

    def test_duplicate_mutation_is_hard_error_and_second_call_does_not_change_state(self) -> None:
        first = self.env.call_tool("refund_order", {"order_id": "O5001", "reason": "defective"})
        self.assertTrue(first.ok)
        self.assertTrue(first.state_changed)
        refunded_amount_after_first = self.env.get_final_state()["orders"]["O5001"]["refunded_amount"]

        second = self.env.call_tool("refund_order", {"order_id": "O5001", "reason": "defective"})
        self.assertFalse(second.ok)
        self.assertEqual(second.error_code, DUPLICATE_MUTATION)
        self.assertFalse(second.state_changed)

        refunded_amount_after_second = self.env.get_final_state()["orders"]["O5001"]["refunded_amount"]
        self.assertEqual(refunded_amount_after_first, refunded_amount_after_second)

        trace = self.env.get_trace()
        self.assertEqual(len(trace), 2)
        self.assertTrue(trace[0]["ok"])
        self.assertFalse(trace[1]["ok"])
        self.assertEqual(trace[1]["error_code"], DUPLICATE_MUTATION)


if __name__ == "__main__":
    unittest.main()
