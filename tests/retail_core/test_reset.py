import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestDeterministicReset(unittest.TestCase):
    def test_same_case_and_seed_reset_is_deterministic(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        first = env.reset(CASE_ID, reset_id="reset-a")
        second = env.reset(CASE_ID, reset_id="reset-b")

        # contract requires state_sha256/entity_counts equality but distinct
        # reset_ids, so evidence from different resets is never mixed.
        self.assertEqual(first["state"]["state_sha256"], second["state"]["state_sha256"])
        self.assertEqual(first["state"]["entity_counts"], second["state"]["entity_counts"])
        self.assertEqual(first["state"]["mutation_count"], 0)
        self.assertEqual(second["state"]["mutation_count"], 0)
        self.assertNotEqual(first["state"]["reset_id"], second["state"]["reset_id"])

    def test_reset_clears_trace_mutation_count_and_ledger(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(CASE_ID, reset_id="reset-1")
        env.call_tool("get_order_details", {"order_id": "O5001"})
        env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
        self.assertEqual(len(env.get_trace()), 2)
        self.assertEqual(env.get_final_state()["mutation_count"], 1)

        env.reset(CASE_ID, reset_id="reset-2")
        self.assertEqual(env.get_trace(), [])
        self.assertEqual(env.get_final_state()["mutation_count"], 0)
        self.assertEqual(env.get_final_state()["sequence_index"], 0)

        # ledger cleared too: the same mutation that succeeded pre-reset
        # must succeed again post-reset instead of being seen as a duplicate.
        retried = env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
        self.assertTrue(retried.ok)

    def test_reset_across_separate_env_instances_is_identical(self) -> None:
        env_a = RetailEnv(DATA_DIR, seed=42)
        env_b = RetailEnv(DATA_DIR, seed=42)
        state_a = env_a.reset(CASE_ID, reset_id="reset-a")["state"]
        state_b = env_b.reset(CASE_ID, reset_id="reset-b")["state"]
        self.assertEqual(state_a["state_sha256"], state_b["state_sha256"])
        self.assertEqual(state_a["entity_counts"], state_b["entity_counts"])


if __name__ == "__main__":
    unittest.main()
