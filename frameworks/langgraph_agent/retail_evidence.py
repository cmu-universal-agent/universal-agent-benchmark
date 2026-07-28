"""Offline wrapper-evidence builder for LangGraph retail (no LLM imports)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = str(ROOT / "verticals" / "retail")
FRAMEWORK_NAME = "langgraph"
WRAPPER_VERSION = "0.1.0"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import TOOL_FAILURE
from adapter.retail_tool_factory import load_contract
from frameworks.langgraph_agent.retail_tools import invoke_retail_tool, make_retail_tools


def build_wrapper_evidence(case_id: str = "RETAIL-E5-001") -> dict[str, Any]:
    """Build offline wrapper-evidence for contract validation (no LLM)."""

    def _scenario_no_tool() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(case_id, reset_id="reset-no-tool", seed=42)
        return env.get_session_evidence("no_tool")

    def _scenario_read_success() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(case_id, reset_id="reset-read-success", seed=42)
        tools = make_retail_tools(env, list(env.allowed_tools))
        invoke_retail_tool(tools, "get_order_details", {"order_id": "O5001"})
        return env.get_session_evidence("read_success")

    def _scenario_write_success() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(case_id, reset_id="reset-write-success", seed=42)
        tools = make_retail_tools(env, list(env.allowed_tools))
        invoke_retail_tool(
            tools,
            "cancel_pending_order",
            {"order_id": "O5003", "reason": "ordered by mistake"},
        )
        return env.get_session_evidence("write_success")

    def _scenario_invalid_arguments() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(case_id, reset_id="reset-invalid-arguments", seed=42)
        # Forward invalid args to RetailEnv; do not pre-validate in the wrapper.
        env.call_tool("return_delivered_order_items", {"order_id": "O5001"})
        return env.get_session_evidence("invalid_arguments")

    def _scenario_disallowed_tool() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(case_id, reset_id="reset-disallowed-tool", seed=42)
        env.allowed_tools = frozenset({"get_order_details"})
        tools = make_retail_tools(env, ["cancel_pending_order"])
        invoke_retail_tool(
            tools,
            "cancel_pending_order",
            {"order_id": "O5003", "reason": "ordered by mistake"},
        )
        return env.get_session_evidence("disallowed_tool")

    def _scenario_tool_failure() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(case_id, reset_id="reset-tool-failure", seed=42)
        tools = make_retail_tools(env, list(env.allowed_tools))
        arguments = {"order_id": "O5003", "reason": "ordered by mistake"}
        env.db.inject_failure(("cancel_pending_order", "O5003"), TOOL_FAILURE)
        invoke_retail_tool(tools, "cancel_pending_order", arguments)
        first_call_id = env.get_trace()[-1]["tool_call_id"]
        env.call_tool("cancel_pending_order", arguments, retry_of=first_call_id)
        return env.get_session_evidence("tool_failure")

    def _scenario_duplicate_action() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        env.reset(case_id, reset_id="reset-duplicate-action", seed=42)
        tools = make_retail_tools(env, list(env.allowed_tools))
        arguments = {"order_id": "O5003", "reason": "ordered by mistake"}
        invoke_retail_tool(tools, "cancel_pending_order", arguments)
        invoke_retail_tool(tools, "cancel_pending_order", arguments)
        return env.get_session_evidence("duplicate_action")

    def _reset_determinism() -> dict[str, Any]:
        env = RetailEnv(DATA_DIR, seed=42)
        first = env.reset(case_id, reset_id="reset-determinism-first", seed=42)["state"]
        second = env.reset(case_id, reset_id="reset-determinism-second", seed=42)["state"]
        return {"seed": 42, "first": first, "second": second}

    contract = load_contract()
    return {
        "contract_version": contract["contract_version"],
        "framework": FRAMEWORK_NAME,
        "wrapper_version": WRAPPER_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reset_determinism": _reset_determinism(),
        "scenarios": [
            _scenario_no_tool(),
            _scenario_read_success(),
            _scenario_write_success(),
            _scenario_invalid_arguments(),
            _scenario_disallowed_tool(),
            _scenario_tool_failure(),
            _scenario_duplicate_action(),
        ],
    }
