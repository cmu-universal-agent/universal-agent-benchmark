"""Confirms the agent-visible/evaluator-only wall in state.py actually
holds: nothing derived from get_evaluator_view() should ever be reachable
through call_tool, get_trace, get_final_state, or get_session_evidence.
"""

import unittest
from pathlib import Path
from typing import Any

from adapter.retail_core.env import RetailEnv

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


def _collect_keys(obj: Any, keys: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            _collect_keys(v, keys)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, keys)


class TestEvaluatorDataLeakage(unittest.TestCase):
    def test_gold_keys_never_reach_agent_visible_outputs(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        reset_payload = env.reset(CASE_ID, reset_id="reset-leakage")
        gold = env.get_evaluator_view()

        # sanity: this case's evaluator_only block is real content worth
        # checking for -- it just happens to be a pending-approval marker
        # (see verticals/retail/cases/RETAIL-E5-001.json) rather than
        # committed gold, since Chloe has not signed off on E5 semantics yet.
        self.assertEqual(gold.get("status"), "pending_chloe_approval")
        self.assertIn("required_actions", gold)

        read_result = env.call_tool("get_order_details", {"order_id": "O5001"})
        mutate_result = env.call_tool(
            "return_delivered_order_items",
            {"order_id": "O5001", "item_ids": ["P1001-BLK"], "payment_method_id": "credit_card_100"},
        )

        agent_visible_keys: set[str] = set()
        _collect_keys(reset_payload, agent_visible_keys)
        _collect_keys(read_result.data, agent_visible_keys)
        _collect_keys(mutate_result.data, agent_visible_keys)
        _collect_keys(env.get_trace(), agent_visible_keys)
        _collect_keys(env.get_final_state(), agent_visible_keys)
        _collect_keys(env.get_session_evidence("leakage-probe"), agent_visible_keys)

        gold_only_keys = {"required_actions", "disallowed_actions", "expected_final_state", "evaluator_only"}
        leaked = gold_only_keys & agent_visible_keys
        self.assertEqual(leaked, set(), f"evaluator-only keys leaked into agent-visible output: {leaked}")

    def test_state_records_never_contain_raw_db_state(self) -> None:
        # A tool's own result (e.g. get_user_details returning a user's
        # address) legitimately contains domain fields -- this checks only
        # the bounded STATE RECORDS (final_state / initial_state), which per
        # docs/ws3_tau_retail_contract.md must contain counts/hash only.
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(CASE_ID, reset_id="reset-leakage-raw")
        env.call_tool("get_user_details", {"user_id": "U100"})

        bounded_keys = {"contract_version", "reset_id", "case_id", "sequence_index", "state_sha256", "entity_counts", "mutation_count"}
        evidence = env.get_session_evidence("raw-state-probe")
        self.assertEqual(set(env.get_final_state()), bounded_keys)
        self.assertEqual(set(evidence["initial_state"]), bounded_keys)
        self.assertEqual(set(evidence["final_state"]), bounded_keys)

    def test_evaluator_view_unavailable_before_reset(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        with self.assertRaises(RuntimeError):
            env.get_evaluator_view()


if __name__ == "__main__":
    unittest.main()
