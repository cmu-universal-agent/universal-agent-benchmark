"""E5 verdict computation: response contract plus final simulator state.

Implements the approved E5 gold semantics in ``docs/e5_gold_semantics_v0.3.md``.
The module accepts an environment factory so the same logic can evaluate a real
retail replay or the synthetic offline smoke fixture.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


PASS = "pass"
FAIL = "fail"
ERROR = "error"

FAILURE_PRECEDENCE = [
    "tool_runtime_failure",
    "disallowed_tool",
    "invalid_arguments",
    "duplicate_side_effect",
    "incorrect_mutation",
    "missing_required_action",
]

PROCESS_VIOLATIONS = {
    "disallowed_tool",
    "invalid_arguments",
    "duplicate_side_effect",
}

REASON_CONTRACT_ONLY = "contract_only_failure"


class Env(Protocol):
    def apply(self, tool_name: str, arguments: dict[str, Any]) -> None: ...

    def hashes(self) -> tuple[str, str]: ...


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    ok: bool = True
    mutated: bool = False
    error: str | None = None


@dataclass
class Trajectory:
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_turns: list[str] = field(default_factory=list)
    terminated_cleanly: bool = True
    runtime_error: str | None = None


def _normalize(
    text: str,
    *,
    case_sensitive: bool,
    collapse_whitespace: bool,
) -> str:
    if not case_sensitive:
        text = text.lower()
    if collapse_whitespace:
        text = re.sub(r"\s+", " ", text)
    return text.strip()


_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _numbers_in(text: str) -> list[float]:
    cleaned = text.replace("$", " ")
    values = []
    for token in _NUMBER_RE.findall(cleaned):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return values


def _item_matches(
    item: dict[str, Any],
    haystack: str,
    raw: str,
    *,
    case_sensitive: bool,
) -> bool:
    kind = item["match_type"]
    if kind == "number":
        tolerance = item.get("tolerance", 0.0)
        return any(
            abs(candidate - float(target)) <= tolerance
            for target in item["values"]
            for candidate in _numbers_in(raw)
        )
    if kind == "regex":
        flags = 0 if case_sensitive else re.IGNORECASE
        return any(re.search(str(value), raw, flags) for value in item["values"])
    values = item["values"] if case_sensitive else [str(value).lower() for value in item["values"]]
    return any(str(value) in haystack for value in values)


def evaluate_response_contract(
    gold: dict[str, Any],
    trajectory: Trajectory,
) -> dict[str, Any]:
    contract = gold["response_contract"]
    matching = contract.get("matching", {})
    case_sensitive = matching.get("case_sensitive", False)
    raw = "\n".join(trajectory.assistant_turns)
    haystack = _normalize(
        raw,
        case_sensitive=case_sensitive,
        collapse_whitespace=matching.get("collapse_whitespace", True),
    )
    required = contract.get("required_info") or []
    if not required and not contract.get("waiver_reason"):
        return {
            "met": False,
            "missing": [],
            "leaked": [],
            "note": "empty required_info with no waiver_reason",
        }
    missing = [
        item["id"]
        for item in required
        if not _item_matches(
            item,
            haystack,
            raw,
            case_sensitive=case_sensitive,
        )
    ]
    leaked = [
        item["id"]
        for item in (contract.get("forbidden_info") or [])
        if _item_matches(
            item,
            haystack,
            raw,
            case_sensitive=case_sensitive,
        )
    ]
    return {"met": not missing and not leaked, "missing": missing, "leaked": leaked}


def evaluate_final_state(
    gold: dict[str, Any],
    trajectory: Trajectory,
    env_factory: Callable[[], Env],
) -> dict[str, Any]:
    gold_env = env_factory()
    for action in gold["gold_write_actions"]:
        try:
            gold_env.apply(action["tool"], action["arguments"])
        except Exception as exc:  # noqa: BLE001 - invalid gold must hard fail
            return {
                "met": False,
                "gold_replay_clean": False,
                "note": f"gold action {action['action_id']} raised: {exc}",
            }

    predicted_env = env_factory()
    for call in trajectory.tool_calls:
        if not call.ok:
            continue
        try:
            predicted_env.apply(call.name, call.arguments)
        except Exception:  # noqa: BLE001 - rejected calls do not mutate
            continue

    gold_agent, gold_user = gold_env.hashes()
    predicted_agent, predicted_user = predicted_env.hashes()
    return {
        "met": (
            gold_agent == predicted_agent
            and gold_user == predicted_user
        ),
        "gold_replay_clean": True,
        "gold_agent_db_hash": gold_agent,
        "gold_user_db_hash": gold_user,
        "predicted_agent_db_hash": predicted_agent,
        "predicted_user_db_hash": predicted_user,
    }


def _canonical(arguments: dict[str, Any]) -> str:
    return json.dumps(arguments, sort_keys=True, default=str)


def classify_failures(
    gold: dict[str, Any],
    trajectory: Trajectory,
    state: dict[str, Any],
) -> list[str]:
    found: set[str] = set()
    if trajectory.runtime_error or not trajectory.terminated_cleanly:
        found.add("tool_runtime_failure")

    allowed = {
        tool
        for bucket in ("read", "write", "generic")
        for tool in (gold["allowed_tools"].get(bucket) or [])
    }
    write_tools = set(gold["allowed_tools"].get("write") or [])
    seen_writes: set[tuple[str, str]] = set()
    for call in trajectory.tool_calls:
        if call.name not in allowed:
            found.add("disallowed_tool")
            continue
        if not call.ok and call.error == "invalid_arguments":
            found.add("invalid_arguments")
        if call.name in write_tools and call.ok and call.mutated:
            key = (call.name, _canonical(call.arguments))
            if key in seen_writes:
                found.add("duplicate_side_effect")
            seen_writes.add(key)

    if not state["met"]:
        mutating = [
            call
            for call in trajectory.tool_calls
            if call.name in write_tools and call.ok and call.mutated
        ]
        required_writes = [
            requirement
            for requirement in gold["required_actions"]
            if requirement["kind"] == "write"
        ]
        found.add(
            "missing_required_action"
            if required_writes and not mutating
            else "incorrect_mutation"
        )

    for requirement in gold["required_actions"]:
        if requirement["kind"] != "terminal":
            continue
        if not any(
            call.name == requirement["tool"] and call.ok
            for call in trajectory.tool_calls
        ):
            found.add("missing_required_action")

    return [
        failure
        for failure in FAILURE_PRECEDENCE
        if failure in found
    ]


def evaluate_case(
    gold: dict[str, Any],
    trajectory: Trajectory,
    env_factory: Callable[[], Env],
) -> dict[str, Any]:
    if trajectory.runtime_error or not trajectory.terminated_cleanly:
        return {
            "case_id": gold["case_id"],
            "verdict": ERROR,
            "criterion_a": None,
            "criterion_b": None,
            "failures": ["tool_runtime_failure"],
            "primary_failure": "tool_runtime_failure",
            "note": trajectory.runtime_error or "did not terminate cleanly",
        }

    contract = evaluate_response_contract(gold, trajectory)
    state = evaluate_final_state(gold, trajectory, env_factory)
    failures = classify_failures(gold, trajectory, state)
    result = {
        "case_id": gold["case_id"],
        "verdict": (
            PASS
            if contract["met"] and state["met"] and not failures
            else FAIL
        ),
        "criterion_a": contract,
        "criterion_b": state,
        "failures": failures,
        "primary_failure": failures[0] if failures else None,
    }
    process_violations = [
        failure for failure in failures if failure in PROCESS_VIOLATIONS
    ]
    if process_violations:
        result["process_violations"] = process_violations
    if not contract["met"]:
        result["response_contract_failure"] = {
            "missing": contract["missing"],
            "leaked": contract["leaked"],
        }
    if state["met"] and not contract["met"]:
        result["sanity_disagreement_reason"] = REASON_CONTRACT_ONLY
    return result
