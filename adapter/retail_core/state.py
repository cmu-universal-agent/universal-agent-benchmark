"""Agent-visible state snapshots and the evaluator-only gold split.

get_evaluator_view() reads straight from the loaded case fixture and must
never be threaded into anything returned by call_tool/get_trace/
get_final_state -- see WS3 build guide section 6/7 and
tests/retail_core/test_leakage.py.
"""

import copy
from typing import Any

from adapter.retail_core.db import RetailDB

EVALUATOR_ONLY_KEY = "evaluator_only"


def agent_visible_state(db: RetailDB) -> dict[str, Any]:
    return {
        "users": copy.deepcopy(db.users),
        "orders": copy.deepcopy(db.orders),
        "products": copy.deepcopy(db.products),
    }


def agent_visible_case(case: dict[str, Any]) -> dict[str, Any]:
    """The parts of a case fixture safe to show the agent (everything
    except the evaluator_only gold block)."""
    return {k: copy.deepcopy(v) for k, v in case.items() if k != EVALUATOR_ONLY_KEY}


def evaluator_view(case: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(case.get(EVALUATOR_ONLY_KEY, {}))
