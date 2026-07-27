"""Confirms the agent-visible/evaluator-only wall in state.py actually
holds: nothing derived from get_evaluator_view() should ever be reachable
through call_tool, get_trace, or get_final_state.
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
        reset_payload = env.reset(CASE_ID)
        gold = env.get_evaluator_view()

        # sanity: the fixture actually has gold content worth checking for
        self.assertIn("required_actions", gold)
        self.assertIn("expected_final_state", gold)

        read_result = env.call_tool("get_order", {"order_id": "O5001"})
        mutate_result = env.call_tool("refund_order", {"order_id": "O5001", "reason": "defective"})

        agent_visible_keys: set[str] = set()
        _collect_keys(reset_payload, agent_visible_keys)
        _collect_keys(read_result.data, agent_visible_keys)
        _collect_keys(mutate_result.data, agent_visible_keys)
        _collect_keys(env.get_trace(), agent_visible_keys)
        _collect_keys(env.get_final_state(), agent_visible_keys)

        gold_only_keys = {"required_actions", "disallowed_actions", "expected_final_state", "evaluator_only"}
        leaked = gold_only_keys & agent_visible_keys
        self.assertEqual(leaked, set(), f"evaluator-only keys leaked into agent-visible output: {leaked}")

    def test_evaluator_view_unavailable_before_reset(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        with self.assertRaises(RuntimeError):
            env.get_evaluator_view()


if __name__ == "__main__":
    unittest.main()
