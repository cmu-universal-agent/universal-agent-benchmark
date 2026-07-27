import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestMutations(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID)

    def test_refund_order_success(self) -> None:
        result = self.env.call_tool("refund_order", {"order_id": "O5001", "reason": "defective"})
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)
        self.assertEqual(result.data["status"], "refunded")
        self.assertEqual(result.data["refunded_amount"], 25.99)

        order = self.env.get_final_state()["orders"]["O5001"]
        self.assertEqual(order["status"], "refunded")
        self.assertEqual(order["refunded_amount"], 25.99)

    def test_exchange_item_success(self) -> None:
        result = self.env.call_tool(
            "exchange_item", {"order_id": "O5001", "old_item_id": "P1001-BLK", "new_item_id": "P1001-WHT"}
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

        order = self.env.get_final_state()["orders"]["O5001"]
        self.assertEqual(order["status"], "exchanged")
        self.assertEqual(order["items"][0]["item_id"], "P1001-WHT")

    def test_return_item_success(self) -> None:
        result = self.env.call_tool("return_item", {"order_id": "O5001", "item_id": "P1001-BLK"})
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

        order = self.env.get_final_state()["orders"]["O5001"]
        self.assertEqual(order["status"], "returned")
        self.assertIn("P1001-BLK", order["returned_items"])

    def test_escalate_to_human_success(self) -> None:
        result = self.env.call_tool("escalate_to_human", {"order_id": "O5001", "reason": "unresolved complaint"})
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)
        self.assertTrue(result.data["ticket_id"])

        order = self.env.get_final_state()["orders"]["O5001"]
        self.assertEqual(len(order["escalations"]), 1)
        self.assertEqual(order["escalations"][0]["ticket_id"], result.data["ticket_id"])


if __name__ == "__main__":
    unittest.main()
