"""Tests for contract-backed retail tool registration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.retail_core.env import RetailEnv
from adapter.retail_tool_factory import canonical_tool_names, load_contract
from frameworks.langgraph_agent.retail_tools import invoke_retail_tool, make_retail_tools


class TestRetailToolRegistration(unittest.TestCase):
    def test_canonical_tool_count_matches_contract(self) -> None:
        contract = load_contract()
        self.assertEqual(len(canonical_tool_names()), len(contract["tools"]))
        self.assertEqual(len(canonical_tool_names()), 15)

    def test_structured_tool_invokes_retail_env(self) -> None:
        env = RetailEnv(str(ROOT / "verticals" / "retail"), seed=42)
        env.reset("RETAIL-E5-001", reset_id="reset-tool-test", seed=42)
        tools = make_retail_tools(env, ["get_order_details"])
        payload = invoke_retail_tool(tools, "get_order_details", {"order_id": "O5001"})
        self.assertTrue(payload["ok"])
        self.assertEqual(len(env.get_trace()), 1)


if __name__ == "__main__":
    unittest.main()
