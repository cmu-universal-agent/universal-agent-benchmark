import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import DISALLOWED_ACTION, INVALID_ARGUMENTS, TOOL_FAILURE
from adapter.retail_core.tools import TOOL_HANDLERS

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestErrors(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID)

    def test_invalid_arguments_missing_field(self) -> None:
        result = self.env.call_tool("refund_order", {"order_id": "O5001"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, INVALID_ARGUMENTS)
        self.assertFalse(result.state_changed)
        order = self.env.get_final_state()["orders"]["O5001"]
        self.assertEqual(order["status"], "delivered")

    def test_disallowed_action_precondition_violation(self) -> None:
        first = self.env.call_tool("refund_order", {"order_id": "O5001", "reason": "defective"})
        self.assertTrue(first.ok)

        result = self.env.call_tool(
            "exchange_item", {"order_id": "O5001", "old_item_id": "P1001-BLK", "new_item_id": "P1001-WHT"}
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, DISALLOWED_ACTION)
        self.assertFalse(result.state_changed)

    def test_tool_failure_never_raises(self) -> None:
        def _boom(db, arguments):
            raise RuntimeError("simulated internal tool failure")

        TOOL_HANDLERS["boom"] = _boom
        try:
            result = self.env.call_tool("boom", {})
        finally:
            del TOOL_HANDLERS["boom"]

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, TOOL_FAILURE)
        self.assertFalse(result.state_changed)
        # the failing call is still recorded, not swallowed
        self.assertEqual(self.env.get_trace()[-1]["tool_name"], "boom")

    def test_unknown_tool_name(self) -> None:
        result = self.env.call_tool("delete_everything", {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, INVALID_ARGUMENTS)


if __name__ == "__main__":
    unittest.main()
