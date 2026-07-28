"""Structured error codes returned by RetailEnv.call_tool.

Mirrors the frozen error table in tools/tau_retail_contract.json /
docs/ws3_tau_retail_contract.md exactly -- error_type, outcome, and the
retryable default are all pinned by the contract, not decided per-handler.
A second group of codes (incorrect_action_order, missing_required_action,
incorrect_final_state, evaluator_data_leakage) is computed by the evaluator
from the trace + final state, not by this module. Do not add those here.
"""

INVALID_ARGUMENTS = "invalid_arguments"
DISALLOWED_TOOL = "disallowed_tool"
NOT_FOUND = "not_found"
INVALID_STATE = "invalid_state"
DUPLICATE_ACTION = "duplicate_action"
POLICY_REJECTED = "policy_rejected"
TOOL_FAILURE = "tool_failure"
TIMEOUT = "timeout"
INTERNAL_ERROR = "internal_error"

# (outcome, retryable_default) per docs/ws3_tau_retail_contract.md's
# Structured errors table / tools/tau_retail_contract.json's "errors" array.
ERROR_TABLE: dict[str, tuple[str, bool]] = {
    INVALID_ARGUMENTS: ("rejected", False),
    DISALLOWED_TOOL: ("rejected", False),
    NOT_FOUND: ("error", False),
    INVALID_STATE: ("error", False),
    DUPLICATE_ACTION: ("error", False),
    POLICY_REJECTED: ("error", False),
    TOOL_FAILURE: ("error", True),
    TIMEOUT: ("timeout", True),
    INTERNAL_ERROR: ("error", False),
}

ALL_CODES = frozenset(ERROR_TABLE)

# Error types a tool handler in tools.py is allowed to return directly.
# invalid_arguments/disallowed_tool are decided centrally by RetailEnv
# before a handler ever runs (schema + allowed_tools checks), so a handler
# returning them would be a contract-shape bug, not a business outcome.
HANDLER_ERROR_CODES = frozenset(
    {
        NOT_FOUND,
        INVALID_STATE,
        DUPLICATE_ACTION,
        POLICY_REJECTED,
        TOOL_FAILURE,
        TIMEOUT,
        INTERNAL_ERROR,
    }
)


def outcome_for(error_type: str) -> str:
    return ERROR_TABLE[error_type][0]


def retryable_default(error_type: str) -> bool:
    return ERROR_TABLE[error_type][1]
