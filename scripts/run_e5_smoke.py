#!/usr/bin/env python3
"""Run public, synthetic controls for the approved E5 evaluator."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.e5_evaluator import (  # noqa: E402
    ERROR,
    FAIL,
    PASS,
    ToolCall,
    Trajectory,
    evaluate_case,
)


class StubRetailEnv:
    def __init__(self) -> None:
        self.db = copy.deepcopy(
            {
                "orders": {
                    "ORDER-SYNTH": {"status": "pending"},
                    "ORDER-OTHER": {"status": "pending"},
                },
                "users": {},
                "products": {},
            }
        )

    def apply(self, tool_name: str, arguments: dict[str, Any]) -> None:
        if tool_name == "transfer_to_human_agents":
            return
        if tool_name != "cancel_pending_order":
            raise ValueError(f"unsupported synthetic tool: {tool_name}")
        order = self.db["orders"].get(arguments["order_id"])
        if order is None:
            raise KeyError(arguments["order_id"])
        if order["status"] != "pending":
            raise ValueError("order is not pending")
        order["status"] = "cancelled"

    def hashes(self) -> tuple[str, str]:
        payload = json.dumps(self.db, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest(), "user-db-inert"


ALLOWED_TOOLS = {
    "read": ["get_order_details"],
    "write": ["cancel_pending_order"],
    "generic": ["transfer_to_human_agents"],
}
GOLD_CALL = ToolCall(
    name="cancel_pending_order",
    arguments={"order_id": "ORDER-SYNTH", "reason": "requested"},
    mutated=True,
)
GOOD_TURN = ["Order ORDER-SYNTH is cancelled."]
GOLD = {
    "case_id": "E5-SYNTH-001",
    "allowed_tools": ALLOWED_TOOLS,
    "gold_write_actions": [
        {
            "action_id": "write-1",
            "tool": "cancel_pending_order",
            "arguments": {"order_id": "ORDER-SYNTH", "reason": "requested"},
        }
    ],
    "required_actions": [
        {
            "id": "required-1",
            "kind": "write",
            "tool": "cancel_pending_order",
        }
    ],
    "response_contract": {
        "required_info": [
            {
                "id": "cancelled-status",
                "match_type": "substring",
                "values": ["cancelled"],
            }
        ],
        "forbidden_info": [
            {
                "id": "unrelated-private-id",
                "match_type": "substring",
                "values": ["PRIVATE-OTHER"],
            }
        ],
        "matching": {"case_sensitive": False, "collapse_whitespace": True},
    },
}
TERMINAL_GOLD = {
    "case_id": "E5-SYNTH-TERMINAL",
    "allowed_tools": ALLOWED_TOOLS,
    "gold_write_actions": [],
    "required_actions": [
        {
            "id": "terminal-1",
            "kind": "terminal",
            "tool": "transfer_to_human_agents",
        }
    ],
    "response_contract": {
        "required_info": [
            {
                "id": "handoff",
                "match_type": "substring",
                "values": ["human agent"],
            }
        ],
        "forbidden_info": [],
    },
}


def main() -> int:
    transfer = ToolCall(
        name="transfer_to_human_agents",
        arguments={"summary": "synthetic handoff"},
    )
    controls = [
        (
            "positive control",
            GOLD,
            Trajectory(tool_calls=[GOLD_CALL], assistant_turns=GOOD_TURN),
            PASS,
            None,
        ),
        (
            "missing required action",
            GOLD,
            Trajectory(assistant_turns=["I will check."]),
            FAIL,
            "missing_required_action",
        ),
        (
            "missing response information",
            GOLD,
            Trajectory(tool_calls=[GOLD_CALL], assistant_turns=["Done."]),
            FAIL,
            None,
        ),
        (
            "duplicate side effect",
            GOLD,
            Trajectory(tool_calls=[GOLD_CALL, GOLD_CALL], assistant_turns=GOOD_TURN),
            FAIL,
            "duplicate_side_effect",
        ),
        (
            "disallowed tool",
            GOLD,
            Trajectory(
                tool_calls=[
                    GOLD_CALL,
                    ToolCall(name="issue_store_credit", arguments={}, mutated=True),
                ],
                assistant_turns=GOOD_TURN,
            ),
            FAIL,
            "disallowed_tool",
        ),
        (
            "invalid arguments",
            GOLD,
            Trajectory(
                tool_calls=[
                    ToolCall(
                        name="cancel_pending_order",
                        arguments={},
                        ok=False,
                        error="invalid_arguments",
                    )
                ],
                assistant_turns=GOOD_TURN,
            ),
            FAIL,
            "invalid_arguments",
        ),
        (
            "forbidden information",
            GOLD,
            Trajectory(
                tool_calls=[GOLD_CALL],
                assistant_turns=GOOD_TURN + ["PRIVATE-OTHER"],
            ),
            FAIL,
            None,
        ),
        (
            "harness error",
            GOLD,
            Trajectory(terminated_cleanly=False, runtime_error="step limit"),
            ERROR,
            "tool_runtime_failure",
        ),
        (
            "terminal positive control",
            TERMINAL_GOLD,
            Trajectory(
                tool_calls=[transfer],
                assistant_turns=["A human agent will continue."],
            ),
            PASS,
            None,
        ),
        (
            "promised handoff without tool",
            TERMINAL_GOLD,
            Trajectory(assistant_turns=["A human agent will continue."]),
            FAIL,
            "missing_required_action",
        ),
        (
            "terminal case mutated state",
            TERMINAL_GOLD,
            Trajectory(
                tool_calls=[
                    transfer,
                    ToolCall(
                        name="cancel_pending_order",
                        arguments={"order_id": "ORDER-OTHER", "reason": "wrong"},
                        mutated=True,
                    ),
                ],
                assistant_turns=["A human agent will continue."],
            ),
            FAIL,
            "incorrect_mutation",
        ),
    ]

    failures = 0
    for label, gold, trajectory, verdict, primary in controls:
        result = evaluate_case(gold, trajectory, StubRetailEnv)
        ok = result["verdict"] == verdict and (
            primary is None or result["primary_failure"] == primary
        )
        print(
            f"[{'ok' if ok else 'FAIL'}] {label}: "
            f"{result['verdict']} / {result['primary_failure']}"
        )
        failures += not ok
    print(f"{len(controls) - failures}/{len(controls)} controls passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
