"""Tests for contract-backed retail tool registration."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from adapter.retail_core.env import RetailEnv
    from adapter.retail_tool_factory import canonical_tool_names, load_contract
    from frameworks.langgraph_agent.retail_tools import (
        invoke_retail_tool,
        make_retail_tools,
    )
except ModuleNotFoundError as exc:
    LANGGRAPH_IMPORT_ERROR = exc
else:
    LANGGRAPH_IMPORT_ERROR = None


@unittest.skipIf(
    LANGGRAPH_IMPORT_ERROR is not None,
    "LangGraph is not installed in this virtual environment",
)
class TestRetailToolRegistration(unittest.TestCase):
    def test_canonical_tool_count_matches_contract(self) -> None:
        contract = load_contract()
        self.assertEqual(len(canonical_tool_names()), len(contract["tools"]))
        self.assertEqual(len(canonical_tool_names()), 16)
        self.assertIn("list_all_product_types", canonical_tool_names())

    def test_structured_tool_invokes_retail_env(self) -> None:
        env = RetailEnv(str(ROOT / "verticals" / "retail"), seed=42)
        env.reset("RETAIL-E5-001", reset_id="reset-tool-test", seed=42)
        tools = make_retail_tools(env, ["get_order_details"])
        payload = invoke_retail_tool(tools, "get_order_details", {"order_id": "O5001"})
        self.assertTrue(payload["ok"])
        self.assertEqual(len(env.get_trace()), 1)

    def test_invalid_arguments_reach_core_with_original_payload(self) -> None:
        env = RetailEnv(str(ROOT / "verticals" / "retail"), seed=42)
        env.reset("RETAIL-E5-001", reset_id="reset-invalid-tool-test", seed=42)
        tools = make_retail_tools(
            env,
            ["get_order_details", "return_delivered_order_items"],
        )
        get_order_schema = next(
            tool.args_schema.model_json_schema()
            for tool in tools
            if tool.name == "get_order_details"
        )
        self.assertEqual(get_order_schema["required"], ["order_id"])
        self.assertFalse(get_order_schema["additionalProperties"])

        missing = {"order_id": "O5001"}
        extra = {"order_id": "O5001", "unexpected": "preserve-me"}
        missing_result = invoke_retail_tool(
            tools,
            "return_delivered_order_items",
            missing,
        )
        extra_result = invoke_retail_tool(
            tools,
            "get_order_details",
            extra,
        )

        self.assertFalse(missing_result["ok"])
        self.assertEqual(missing_result["error_type"], "invalid_arguments")
        self.assertFalse(extra_result["ok"])
        self.assertEqual(extra_result["error_type"], "invalid_arguments")
        trace = env.get_trace()
        self.assertEqual(trace[0]["arguments"], missing)
        self.assertEqual(trace[1]["arguments"], extra)
        self.assertFalse(trace[0]["arguments_valid"])
        self.assertFalse(trace[1]["arguments_valid"])


if __name__ == "__main__":
    unittest.main()
