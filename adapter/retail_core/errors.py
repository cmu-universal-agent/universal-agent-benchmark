"""Structured error codes returned by RetailEnv.call_tool.

These are the ONLY error codes the simulator itself raises (Group A in the
WS3 build guide -- runtime/business failures observed on a single tool
call). A second group of codes (incorrect_action_order,
missing_required_action, incorrect_final_state, evaluator_data_leakage) is
computed by the evaluator from the trace + final state, not by this module.
Do not add those here.
"""

INVALID_ARGUMENTS = "invalid_arguments"
DISALLOWED_ACTION = "disallowed_action"
TOOL_FAILURE = "tool_failure"
DUPLICATE_MUTATION = "duplicate_mutation"

ALL_CODES = {INVALID_ARGUMENTS, DISALLOWED_ACTION, TOOL_FAILURE, DUPLICATE_MUTATION}
