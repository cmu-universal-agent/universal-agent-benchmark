import json
import unittest
from pathlib import Path

import jsonschema

from adapter.retail_core.env import RetailEnv

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"
STATE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "tau_retail_state_record.schema.json"


class TestFinalState(unittest.TestCase):
    def setUp(self) -> None:
        schema = json.loads(STATE_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.state_validator = jsonschema.Draft202012Validator(schema)

    def test_final_state_is_bounded_evidence_not_raw_state(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(CASE_ID, reset_id="reset-final-state")

        env.call_tool("get_order_details", {"order_id": "O5001"})  # read, no effect on final state
        result = env.call_tool(
            "return_delivered_order_items",
            {"order_id": "O5001", "item_ids": ["P1001-BLK"], "payment_method_id": "credit_card_100"},
        )
        self.assertTrue(result.ok)

        final_state = env.get_final_state()
        errors = list(self.state_validator.iter_errors(final_state))
        self.assertEqual(errors, [], f"final state violates the schema: {errors}")

        # bounded means counts/hash only -- never raw users/orders/products.
        self.assertNotIn("orders", final_state)
        self.assertNotIn("users", final_state)
        self.assertNotIn("products", final_state)
        self.assertEqual(final_state["entity_counts"], {"orders": 3, "products": 2, "users": 2})
        self.assertEqual(final_state["mutation_count"], 1)
        self.assertEqual(final_state["sequence_index"], 2)

    def test_failed_operations_do_not_alter_bounded_state(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(CASE_ID, reset_id="reset-failed-ops")
        before = env.get_final_state()

        env.call_tool("get_order_details", {"order_id": "O9999"})  # not_found
        env.call_tool("return_delivered_order_items", {"order_id": "O5001"})  # invalid_arguments

        after = env.get_final_state()
        self.assertEqual(before["state_sha256"], after["state_sha256"])
        self.assertEqual(before["entity_counts"], after["entity_counts"])
        self.assertEqual(before["mutation_count"], after["mutation_count"])
        # sequence_index does advance -- both failed attempts are still
        # recorded in the trace, per the contract's mutation-evidence rules.
        self.assertEqual(after["sequence_index"], 2)


if __name__ == "__main__":
    unittest.main()
