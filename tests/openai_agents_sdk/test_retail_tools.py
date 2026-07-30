"""Tests for OpenAI Agents SDK retail tool registration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.retail_core.env import RetailEnv
from adapter.retail_tool_factory import canonical_tool_names, load_contract
from frameworks.openai_agents_sdk.retail_tools import (
    invoke_retail_tool,
    make_retail_tools,
)


class TestOpenAIRetailToolRegistration(unittest.TestCase):
    def test_canonical_tool_count_matches_contract(self) -> None:
        contract = load_contract()
        self.assertEqual(len(canonical_tool_names()), len(contract["tools"]))
        self.assertEqual(len(canonical_tool_names()), 16)
        self.assertIn("list_all_product_types", canonical_tool_names())
        env = RetailEnv(str(ROOT / "verticals" / "retail"), seed=42)
        env.reset("RETAIL-E5-001", reset_id="reset-openai-registry", seed=42)
        self.assertEqual(
            {tool.name for tool in make_retail_tools(env)},
            set(canonical_tool_names()),
        )

    def test_invoke_forwards_to_retail_env(self) -> None:
        env = RetailEnv(str(ROOT / "verticals" / "retail"), seed=42)
        env.reset("RETAIL-E5-001", reset_id="reset-openai-tool-test", seed=42)
        tools = make_retail_tools(env, ["get_order_details"])
        payload = invoke_retail_tool(
            tools,
            "get_order_details",
            {"order_id": "O5001"},
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(len(env.get_trace()), 1)

    def test_invalid_arguments_reach_shared_core(self) -> None:
        env = RetailEnv(str(ROOT / "verticals" / "retail"), seed=42)
        env.reset("RETAIL-E5-001", reset_id="reset-openai-invalid", seed=42)
        tools = make_retail_tools(env, ["return_delivered_order_items"])
        payload = invoke_retail_tool(
            tools,
            "return_delivered_order_items",
            {"order_id": "O5001"},
        )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error_type"], "invalid_arguments")
        self.assertEqual(
            env.get_trace()[0]["arguments"],
            {"order_id": "O5001"},
        )


if __name__ == "__main__":
    unittest.main()
