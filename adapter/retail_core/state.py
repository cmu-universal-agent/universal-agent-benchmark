"""Agent-visible case snapshots and the evaluator-only gold split.

Raw RetailDB state (.users/.orders/.products) has no agent- or
evaluator-visible accessor here on purpose: per
docs/ws3_tau_retail_contract.md, "raw database state remains
evaluator-only," and even the evaluator only ever sees the bounded record
from RetailDB.state_record() (see env.py's get_final_state/
get_session_evidence). get_evaluator_view() reads straight from the loaded
case fixture and must never be threaded into anything returned by
call_tool/get_trace/get_final_state -- see tests/retail_core/test_leakage.py.
"""

import copy
from typing import Any

EVALUATOR_ONLY_KEY = "evaluator_only"


def agent_visible_case(case: dict[str, Any]) -> dict[str, Any]:
    """The parts of a case fixture safe to show the agent (everything
    except the evaluator_only gold block)."""
    return {k: copy.deepcopy(v) for k, v in case.items() if k != EVALUATOR_ONLY_KEY}


def evaluator_view(case: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(case.get(EVALUATOR_ONLY_KEY, {}))
