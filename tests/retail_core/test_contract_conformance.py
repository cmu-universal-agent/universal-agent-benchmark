"""End-to-end proof that RetailEnv actually satisfies the WS3 canonical
contract (tools/tau_retail_contract.json), not just that its own unit tests
pass. Drives a real RetailEnv through the seven fixture scenarios the
contract requires and feeds the resulting wrapper-evidence envelope through
scripts/validate_ws3_tau_retail_contract.py -- the same command a framework
wrapper author is told to run in docs/ws3_tau_retail_contract.md.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from adapter.retail_core.env import RetailEnv
from adapter.retail_core.errors import TOOL_FAILURE
from adapter.retail_core.tools import TOOL_HANDLERS

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = str(ROOT / "verticals" / "retail")
CASE_ID = "RETAIL-E5-001"
VALIDATOR = ROOT / "scripts" / "validate_ws3_tau_retail_contract.py"
CONTRACT_PATH = ROOT / "tools" / "tau_retail_contract.json"


def _scenario_no_tool() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    env.reset(CASE_ID, reset_id="reset-no-tool", seed=42)
    return env.get_session_evidence("no_tool")


def _scenario_read_success() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    env.reset(CASE_ID, reset_id="reset-read-success", seed=42)
    env.call_tool("get_order_details", {"order_id": "O5001"})
    return env.get_session_evidence("read_success")


def _scenario_write_success() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    env.reset(CASE_ID, reset_id="reset-write-success", seed=42)
    env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
    return env.get_session_evidence("write_success")


def _scenario_invalid_arguments() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    env.reset(CASE_ID, reset_id="reset-invalid-arguments", seed=42)
    env.call_tool("return_delivered_order_items", {"order_id": "O5001"})
    return env.get_session_evidence("invalid_arguments")


def _scenario_disallowed_tool() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    env.reset(CASE_ID, reset_id="reset-disallowed-tool", seed=42)
    env.allowed_tools = frozenset({"get_order_details"})
    env.call_tool("cancel_pending_order", {"order_id": "O5003", "reason": "ordered by mistake"})
    return env.get_session_evidence("disallowed_tool")


def _scenario_tool_failure() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    env.reset(CASE_ID, reset_id="reset-tool-failure", seed=42)
    arguments = {"order_id": "O5003", "reason": "ordered by mistake"}
    env.db.inject_failure(("cancel_pending_order", "O5003"), TOOL_FAILURE)
    env.call_tool("cancel_pending_order", arguments)
    first_call_id = env.get_trace()[-1]["tool_call_id"]
    env.call_tool("cancel_pending_order", arguments, retry_of=first_call_id)
    return env.get_session_evidence("tool_failure")


def _scenario_duplicate_action() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    env.reset(CASE_ID, reset_id="reset-duplicate-action", seed=42)
    arguments = {"order_id": "O5003", "reason": "ordered by mistake"}
    env.call_tool("cancel_pending_order", arguments)
    env.call_tool("cancel_pending_order", arguments)
    return env.get_session_evidence("duplicate_action")


def _reset_determinism() -> dict:
    env = RetailEnv(DATA_DIR, seed=42)
    first = env.reset(CASE_ID, reset_id="reset-determinism-first", seed=42)["state"]
    second = env.reset(CASE_ID, reset_id="reset-determinism-second", seed=42)["state"]
    return {"seed": 42, "first": first, "second": second}


def build_wrapper_evidence() -> dict:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return {
        "contract_version": contract["contract_version"],
        "framework": "langgraph",
        "wrapper_version": "retail-core-contract-conformance-test",
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


class TestCanonicalToolRegistry(unittest.TestCase):
    def test_tool_handlers_match_the_frozen_contract_exactly(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract_tools = {tool["name"] for tool in contract["tools"]}
        self.assertEqual(set(TOOL_HANDLERS), contract_tools)
        self.assertEqual(len(contract_tools), 16)


class TestWrapperEvidenceConformance(unittest.TestCase):
    def test_real_retail_env_session_satisfies_the_ws3_contract_validator(self) -> None:
        evidence = build_wrapper_evidence()
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "wrapper_evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--wrapper-evidence", str(evidence_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WS3_TAU_RETAIL_CONTRACT_OK", result.stdout)
        self.assertIn("wrapper_evidence=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
