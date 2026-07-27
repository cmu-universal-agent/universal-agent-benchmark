import json
import unittest
from pathlib import Path

from adapter.retail_core.env import RetailEnv

DATA_DIR = str(Path(__file__).resolve().parents[2] / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"


class TestDeterministicReset(unittest.TestCase):
    def test_reset_twice_is_byte_identical(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        first = env.reset(CASE_ID)
        second = env.reset(CASE_ID)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_reset_clears_trace(self) -> None:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(CASE_ID)
        env.call_tool("get_order", {"order_id": "O5001"})
        self.assertEqual(len(env.get_trace()), 1)
        env.reset(CASE_ID)
        self.assertEqual(env.get_trace(), [])

    def test_reset_across_separate_env_instances_is_identical(self) -> None:
        env_a = RetailEnv(DATA_DIR, seed=42)
        env_b = RetailEnv(DATA_DIR, seed=42)
        state_a = env_a.reset(CASE_ID)
        state_b = env_b.reset(CASE_ID)
        self.assertEqual(json.dumps(state_a, sort_keys=True), json.dumps(state_b, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
