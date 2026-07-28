import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import (
    DISALLOWED_TOOL,
    INTERNAL_ERROR,
    INVALID_ARGUMENTS,
    INVALID_STATE,
    NOT_FOUND,
    TOOL_FAILURE,
)

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestErrors(unittest.TestCase):
    def setUp(self) -> None:
        self.env = RetailEnv(DATA_DIR, seed=42)
        self.env.reset(CASE_ID, reset_id="reset-errors")

    def test_invalid_arguments_missing_field(self) -> None:
        result = self.env.call_tool("return_delivered_order_items", {"order_id": "O5001"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, INVALID_ARGUMENTS)
        self.assertFalse(result.state_changed)
        order = self.env.db.get_order("O5001")
        self.assertEqual(order["status"], "delivered")

    def test_not_found_unknown_payment_method(self) -> None:
        result = self.env.call_tool(
            "return_delivered_order_items",
            {"order_id": "O5001", "item_ids": ["P1001-BLK"], "payment_method_id": "does_not_exist"},
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, NOT_FOUND)
        self.assertFalse(result.state_changed)

    def test_invalid_state_precondition_violation(self) -> None:
        first = self.env.call_tool(
            "return_delivered_order_items",
            {"order_id": "O5001", "item_ids": ["P1001-BLK"], "payment_method_id": "credit_card_100"},
        )
        self.assertTrue(first.ok)

        # order O5001 is now "return_requested", no longer "delivered"
        result = self.env.call_tool(
            "exchange_delivered_order_items",
            {
                "order_id": "O5001",
                "item_ids": ["P1001-BLK"],
                "new_item_ids": ["P1001-WHT"],
                "payment_method_id": "credit_card_100",
            },
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, INVALID_STATE)
        self.assertFalse(result.state_changed)

    def test_disallowed_tool_when_not_in_allowed_tools(self) -> None:
        self.env.allowed_tools = frozenset({"get_order_details"})
        result = self.env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, DISALLOWED_TOOL)
        self.assertFalse(result.state_changed)

    def test_unknown_tool_name_is_disallowed_tool(self) -> None:
        result = self.env.call_tool("delete_everything", {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, DISALLOWED_TOOL)

    def test_internal_error_on_calculate_division_by_zero(self) -> None:
        result = self.env.call_tool("calculate", {"expression": "5 / 0"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_type, INTERNAL_ERROR)
        self.assertFalse(result.state_changed)

    def test_injected_tool_failure_never_raises_and_clears_after_one_attempt(self) -> None:
        self.env.db.inject_failure(("cancel_pending_order", "O5003"), TOOL_FAILURE)

        failed = self.env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
        self.assertFalse(failed.ok)
        self.assertEqual(failed.error_type, TOOL_FAILURE)
        self.assertFalse(failed.state_changed)

        retried = self.env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
        self.assertTrue(retried.ok)
        self.assertTrue(retried.state_changed)

        trace = self.env.get_trace()
        self.assertEqual(len(trace), 2)
        self.assertEqual(trace[0]["outcome"], "error")
        self.assertTrue(trace[0]["error"]["retryable"])
        self.assertEqual(trace[1]["outcome"], "success")


if __name__ == "__main__":
    unittest.main()
