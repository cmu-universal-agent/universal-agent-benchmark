import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestMutations(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID, reset_id="reset-mutations")

    def test_cancel_pending_order_success(self) -> None:
        result = self.env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

        order = self.env.db.get_order("O5003")
        self.assertEqual(order["status"], "cancelled")
        self.assertEqual(self.env.get_final_state()["mutation_count"], 1)

    def test_exchange_delivered_order_items_success(self) -> None:
        result = self.env.call_tool(
            "exchange_delivered_order_items",
            {
                "order_id": "O5001",
                "item_ids": ["P1001-BLK"],
                "new_item_ids": ["P1001-WHT"],
                "payment_method_id": "credit_card_100",
            },
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

        order = self.env.db.get_order("O5001")
        self.assertEqual(order["status"], "exchange_requested")
        self.assertEqual(order["items"][0]["item_id"], "P1001-WHT")

    def test_return_delivered_order_items_success(self) -> None:
        result = self.env.call_tool(
            "return_delivered_order_items",
            {"order_id": "O5001", "item_ids": ["P1001-BLK"], "payment_method_id": "credit_card_100"},
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)
        self.assertAlmostEqual(result.data["refund_amount"], 25.99)

        order = self.env.db.get_order("O5001")
        self.assertEqual(order["status"], "return_requested")
        self.assertIn("P1001-BLK", order["returned_items"])

    def test_modify_pending_order_items_success(self) -> None:
        result = self.env.call_tool(
            "modify_pending_order_items",
            {
                "order_id": "O5003",
                "item_ids": ["P1002-STD"],
                "new_item_ids": ["P1002-ISO"],
                "payment_method_id": "credit_card_101",
            },
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

        order = self.env.db.get_order("O5003")
        self.assertEqual(order["items"][0]["item_id"], "P1002-ISO")
        self.assertAlmostEqual(order["total"], 92.0)

    def test_modify_pending_order_payment_success(self) -> None:
        result = self.env.call_tool(
            "modify_pending_order_payment", {"order_id": "O5003", "payment_method_id": "credit_card_101"}
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

    def test_modify_pending_order_address_success(self) -> None:
        address = {
            "order_id": "O5003",
            "address1": "500 New St",
            "address2": "",
            "city": "Boston",
            "state": "MA",
            "country": "USA",
            "zip": "02110",
        }
        result = self.env.call_tool("modify_pending_order_address", address)
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

        order = self.env.db.get_order("O5003")
        self.assertEqual(order["address"]["city"], "Boston")

    def test_modify_user_address_success(self) -> None:
        address = {
            "user_id": "U101",
            "address1": "9 New Ave",
            "address2": "",
            "city": "Boston",
            "state": "MA",
            "country": "USA",
            "zip": "02110",
        }
        result = self.env.call_tool("modify_user_address", address)
        self.assertTrue(result.ok)
        self.assertTrue(result.state_changed)

        user = self.env.db.get_user("U101")
        self.assertEqual(user["address"]["city"], "Boston")

    def test_transfer_to_human_agents_success_and_non_mutating(self) -> None:
        before = self.env.get_final_state()["state_sha256"]
        result = self.env.call_tool("transfer_to_human_agents", {"summary": "customer needs a supervisor"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertTrue(result.data["ticket_id"])
        after = self.env.get_final_state()["state_sha256"]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
