import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import INVALID_ARGUMENTS, NOT_FOUND

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestReadTools(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID, reset_id="reset-read-tools")

    def test_get_order_details_success(self) -> None:
        result = self.env.call_tool("get_order_details", {"order_id": "O5001"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(result.data["order_id"], "O5001")
        self.assertEqual(result.data["status"], "delivered")

    def test_get_user_details_success(self) -> None:
        result = self.env.call_tool("get_user_details", {"user_id": "U100"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(result.data["user_id"], "U100")

    def test_get_product_details_success(self) -> None:
        result = self.env.call_tool("get_product_details", {"product_id": "P1001"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(len(result.data["variants"]), 2)

    def test_get_item_details_success(self) -> None:
        result = self.env.call_tool("get_item_details", {"item_id": "P1001-BLK"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(result.data["item_id"], "P1001-BLK")

    def test_list_all_product_types_success(self) -> None:
        result = self.env.call_tool("list_all_product_types", {})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(
            result.data,
            {"Mechanical Keyboard": "P1002", "Wireless Mouse": "P1001"},
        )

    def test_find_user_id_by_email_success(self) -> None:
        result = self.env.call_tool("find_user_id_by_email", {"email": "alice@example.com"})
        self.assertTrue(result.ok)
        self.assertEqual(result.data["user_id"], "U100")

    def test_find_user_id_by_name_zip_success(self) -> None:
        result = self.env.call_tool(
            "find_user_id_by_name_zip", {"first_name": "Ben", "last_name": "Ortiz", "zip": "10001"}
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.data["user_id"], "U101")

    def test_calculate_success(self) -> None:
        result = self.env.call_tool("calculate", {"expression": "25.99 + 89.0"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertAlmostEqual(result.data["result"], 114.99)

    def test_get_order_unknown_id_is_not_found(self) -> None:
        result = self.env.call_tool("get_order_details", {"order_id": "O9999"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, NOT_FOUND)
        self.assertFalse(result.state_changed)

    def test_get_order_missing_argument_is_invalid_arguments(self) -> None:
        result = self.env.call_tool("get_order_details", {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, INVALID_ARGUMENTS)


if __name__ == "__main__":
    unittest.main()
