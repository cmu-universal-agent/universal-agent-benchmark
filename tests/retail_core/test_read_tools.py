import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import DISALLOWED_ACTION, INVALID_ARGUMENTS

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestReadTools(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID)

    def test_get_order_success(self) -> None:
        result = self.env.call_tool("get_order", {"order_id": "O5001"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(result.data["order_id"], "O5001")
        self.assertEqual(result.data["status"], "delivered")

    def test_get_user_success(self) -> None:
        result = self.env.call_tool("get_user", {"user_id": "U100"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(result.data["user_id"], "U100")

    def test_get_product_success(self) -> None:
        result = self.env.call_tool("get_product", {"product_id": "P1001"})
        self.assertTrue(result.ok)
        self.assertFalse(result.state_changed)
        self.assertEqual(len(result.data["variants"]), 2)

    def test_get_order_unknown_id(self) -> None:
        result = self.env.call_tool("get_order", {"order_id": "O9999"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, DISALLOWED_ACTION)
        self.assertFalse(result.state_changed)

    def test_get_order_missing_argument(self) -> None:
        result = self.env.call_tool("get_order", {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, INVALID_ARGUMENTS)


if __name__ == "__main__":
    unittest.main()
