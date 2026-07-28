#!/usr/bin/env python3
"""Validate the WS3 tau-retail candidate contract without model calls or data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.validation import (  # noqa: E402
    FORBIDDEN_AGENT_VISIBLE_KEYS,
    validate_tool_call_constraints,
)


CONTRACT_PATH = ROOT / "tools" / "tau_retail_contract.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "tau_retail_contract_cases.json"
STATE_SCHEMA_PATH = ROOT / "schemas" / "tau_retail_state_record.schema.json"
SESSION_SCHEMA_PATH = ROOT / "schemas" / "tau_retail_session_evidence.schema.json"
WRAPPER_SCHEMA_PATH = ROOT / "schemas" / "tau_retail_wrapper_evidence.schema.json"
TOOL_CALL_SCHEMA_PATH = ROOT / "schemas" / "tool_call.schema.json"

EXPECTED_TOOLS = {
    "calculate",
    "cancel_pending_order",
    "exchange_delivered_order_items",
    "find_user_id_by_email",
    "find_user_id_by_name_zip",
    "get_item_details",
    "get_order_details",
    "get_product_details",
    "get_user_details",
    "list_all_product_types",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "modify_user_address",
    "return_delivered_order_items",
    "transfer_to_human_agents",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _forbidden_paths(value: Any, path: str = "<root>") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_AGENT_VISIBLE_KEYS:
                found.append(child_path)
            found.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return found


def _validate_registry(contract: dict[str, Any], fixture: dict[str, Any]) -> dict[str, str]:
    _assert(contract["contract_version"] == fixture["contract_version"], "contract/fixture version mismatch")
    tools = contract["tools"]
    names = [tool["name"] for tool in tools]
    _assert(len(names) == len(set(names)), "duplicate canonical tool name")
    _assert(set(names) == EXPECTED_TOOLS, "canonical tool set drift")
    _assert(set(fixture["valid_arguments"]) == EXPECTED_TOOLS, "argument fixture coverage drift")

    operations: dict[str, str] = {}
    for tool in tools:
        name = tool["name"]
        operations[name] = tool["operation"]
        _assert(
            tool["operation"] in {"read", "write", "non_mutating"},
            f"invalid operation for {name}",
        )
        schema_path = ROOT / tool["input_schema"]
        _assert(schema_path.is_file(), f"missing input schema for {name}")
        schema = _load(schema_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        valid_errors = list(validator.iter_errors(fixture["valid_arguments"][name]))
        _assert(not valid_errors, f"valid argument fixture failed for {name}: {valid_errors}")
        if fixture["valid_arguments"][name]:
            _assert(list(validator.iter_errors({})), f"empty arguments unexpectedly passed for {name}")
    return operations


def _validate_state(validator: jsonschema.Draft202012Validator, state: dict[str, Any]) -> None:
    errors = list(validator.iter_errors(state))
    _assert(not errors, f"invalid state evidence: {errors}")


def _validate_scenarios(
    contract: dict[str, Any], fixture: dict[str, Any], operations: dict[str, str]
) -> tuple[int, int]:
    state_schema = _load(STATE_SCHEMA_PATH)
    session_schema = _load(SESSION_SCHEMA_PATH)
    tool_call_schema = _load(TOOL_CALL_SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(state_schema)
    jsonschema.Draft202012Validator.check_schema(session_schema)
    jsonschema.Draft202012Validator.check_schema(tool_call_schema)
    registry = Registry().with_resources(
        [
            (state_schema["$id"], Resource.from_contents(state_schema)),
            (tool_call_schema["$id"], Resource.from_contents(tool_call_schema)),
        ]
    )
    state_validator = jsonschema.Draft202012Validator(state_schema)
    tool_validator = jsonschema.Draft202012Validator(
        tool_call_schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    session_validator = jsonschema.Draft202012Validator(
        session_schema,
        registry=registry,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    errors_by_type = {row["error_type"]: row for row in contract["errors"]}
    argument_validators = {
        tool["name"]: jsonschema.Draft202012Validator(
            _load(ROOT / tool["input_schema"])
        )
        for tool in contract["tools"]
    }

    reset = fixture["reset_determinism"]
    for state in (reset["first"], reset["second"]):
        _validate_state(state_validator, state)
        _assert(state["mutation_count"] == 0, "reset must clear mutation count")
    _assert(reset["first"]["case_id"] == reset["second"]["case_id"], "reset cases differ")
    _assert(reset["first"]["reset_id"] != reset["second"]["reset_id"], "reset ids must differ")
    _assert(reset["first"]["state_sha256"] == reset["second"]["state_sha256"], "same case/seed reset is not deterministic")
    _assert(reset["first"]["entity_counts"] == reset["second"]["entity_counts"], "same case/seed reset counts differ")

    calls = 0
    fixture_ids: set[str] = set()
    for scenario in fixture["scenarios"]:
        fixture_id = scenario["fixture_id"]
        _assert(fixture_id not in fixture_ids, f"duplicate fixture id: {fixture_id}")
        fixture_ids.add(fixture_id)
        session_errors = list(session_validator.iter_errors(scenario))
        _assert(not session_errors, f"session evidence schema failure in {fixture_id}: {session_errors}")
        initial = scenario["initial_state"]
        final = scenario["final_state"]
        _validate_state(state_validator, initial)
        _validate_state(state_validator, final)
        _assert(initial["reset_id"] == final["reset_id"], f"reset id drift in {fixture_id}")
        _assert(initial["case_id"] == final["case_id"], f"case id drift in {fixture_id}")
        _assert(initial["sequence_index"] == 0, f"initial sequence is not zero in {fixture_id}")
        _assert(initial["mutation_count"] == 0, f"initial mutation count is not zero in {fixture_id}")

        events = scenario["events"]
        _assert(final["sequence_index"] == len(events), f"final sequence mismatch in {fixture_id}")
        expected_before = initial["state_sha256"]
        successful_writes = 0
        calls_by_id: dict[str, dict[str, Any]] = {}
        run_id: str | None = None
        for index, event in enumerate(events):
            call = event["call"]
            calls += 1
            schema_errors = list(tool_validator.iter_errors(call))
            _assert(not schema_errors, f"tool-call schema failure in {fixture_id}: {schema_errors}")
            _assert(not validate_tool_call_constraints(call), f"tool-call semantic failure in {fixture_id}")
            _assert(call["sequence_index"] == index, f"non-contiguous call order in {fixture_id}")
            _assert(call["tool_call_id"] not in calls_by_id, f"duplicate call id in {fixture_id}")
            _assert(call["tool_name"] in operations, f"unknown canonical tool in {fixture_id}")
            computed_allowed = call["tool_name"] in scenario["allowed_tools"]
            computed_valid = not list(
                argument_validators[call["tool_name"]].iter_errors(call["arguments"])
            )
            _assert(call["was_allowed"] == computed_allowed, f"allowed-tools mismatch in {fixture_id}")
            _assert(call["arguments_valid"] == computed_valid, f"argument-validity mismatch in {fixture_id}")
            if run_id is None:
                run_id = call["run_id"]
            _assert(call["run_id"] == run_id, f"mixed run ids in {fixture_id}")
            if call["retry_of"] is not None:
                _assert(call["retry_of"] in calls_by_id, f"retry does not reference an earlier call in {fixture_id}")
                _assert(
                    calls_by_id[call["retry_of"]]["retry_of"] is None,
                    f"retry does not reference the root attempt in {fixture_id}",
                )
            calls_by_id[call["tool_call_id"]] = call
            _assert(event["state_before_sha256"] == expected_before, f"state chain break in {fixture_id}")

            operation = operations[call["tool_name"]]
            changed = event["state_before_sha256"] != event["state_after_sha256"]
            if call["outcome"] == "success":
                _assert(call["was_allowed"] and call["arguments_valid"], f"invalid success in {fixture_id}")
                _assert(call["error"] is None, f"success contains error in {fixture_id}")
                if operation == "write":
                    _assert(changed, f"successful write did not mutate state in {fixture_id}")
                    successful_writes += 1
                else:
                    _assert(not changed, f"read mutated state in {fixture_id}")
            else:
                _assert(not changed, f"non-success mutated state in {fixture_id}")
                error = call["error"]
                _assert(error is not None, f"non-success missing error in {fixture_id}")
                rule = errors_by_type.get(error["error_type"])
                _assert(rule is not None, f"unknown structured error in {fixture_id}")
                _assert(rule["outcome"] == call["outcome"], f"error/outcome mismatch in {fixture_id}")
                _assert(rule["retryable"] == error["retryable"], f"retry default mismatch in {fixture_id}")
                if error["error_type"] == "invalid_arguments":
                    _assert(not call["arguments_valid"], f"invalid_arguments lacks invalid arguments in {fixture_id}")
                if error["error_type"] == "disallowed_tool":
                    _assert(not call["was_allowed"], f"disallowed_tool was allowed in {fixture_id}")
                if call["outcome"] == "rejected":
                    _assert(not call["was_allowed"] or not call["arguments_valid"], f"rejection lacks cause in {fixture_id}")
            expected_before = event["state_after_sha256"]

        _assert(final["state_sha256"] == expected_before, f"final state mismatch in {fixture_id}")
        _assert(final["mutation_count"] == successful_writes, f"mutation count mismatch in {fixture_id}")

    required = {"no_tool", "read_success", "write_success", "invalid_arguments", "disallowed_tool", "tool_failure", "duplicate_action"}
    _assert(fixture_ids == required, "minimum fixture set drift")
    duplicate = next(row for row in fixture["scenarios"] if row["fixture_id"] == "duplicate_action")
    _assert(duplicate["events"][-1]["call"]["error"]["error_type"] == "duplicate_action", "duplicate fixture lacks duplicate_action")
    _assert(duplicate["final_state"]["mutation_count"] == 1, "duplicate action mutated more than once")
    failure = next(
        row for row in fixture["scenarios"] if row["fixture_id"] == "tool_failure"
    )
    _assert(
        failure["events"][0]["call"]["error"]["error_type"] == "tool_failure",
        "tool-failure fixture lacks an injected failure",
    )
    _assert(
        failure["events"][1]["call"]["retry_of"]
        == failure["events"][0]["call"]["tool_call_id"],
        "tool-failure recovery is not linked to the root attempt",
    )
    _assert(
        failure["events"][1]["call"]["outcome"] == "success",
        "tool-failure fixture lacks a successful recovery",
    )
    return len(fixture_ids), calls


def _validate_leakage(fixture: dict[str, Any]) -> None:
    probe = fixture["leakage_probe"]
    _assert(not _forbidden_paths(probe["agent_visible_good"]), "safe leakage fixture was rejected")
    _assert(_forbidden_paths(probe["agent_visible_bad"]), "forbidden evaluator key was not detected")
    for scenario in fixture["scenarios"]:
        for event in scenario["events"]:
            _assert(not _forbidden_paths(event["call"]["result"]), f"agent-visible tool result leaks evaluator data in {scenario['fixture_id']}")


def _validate_wrapper_envelope(evidence: dict[str, Any]) -> None:
    state_schema = _load(STATE_SCHEMA_PATH)
    session_schema = _load(SESSION_SCHEMA_PATH)
    tool_call_schema = _load(TOOL_CALL_SCHEMA_PATH)
    wrapper_schema = _load(WRAPPER_SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(wrapper_schema)
    registry = Registry().with_resources(
        [
            (state_schema["$id"], Resource.from_contents(state_schema)),
            (session_schema["$id"], Resource.from_contents(session_schema)),
            (tool_call_schema["$id"], Resource.from_contents(tool_call_schema)),
        ]
    )
    validator = jsonschema.Draft202012Validator(
        wrapper_schema,
        registry=registry,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    errors = list(validator.iter_errors(evidence))
    _assert(not errors, f"wrapper evidence schema failure: {errors}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wrapper-evidence",
        action="append",
        default=[],
        type=Path,
        help="Optional wrapper evidence JSON; repeat for multiple frameworks.",
    )
    args = parser.parse_args()
    contract = _load(CONTRACT_PATH)
    fixture = _load(FIXTURE_PATH)
    operations = _validate_registry(contract, fixture)
    scenarios, calls = _validate_scenarios(contract, fixture, operations)
    _validate_leakage(fixture)
    synthetic_evidence = {
        "contract_version": contract["contract_version"],
        "framework": "langgraph",
        "wrapper_version": "synthetic-contract-fixture",
        "generated_at": "2026-07-22T00:00:00Z",
        "reset_determinism": fixture["reset_determinism"],
        "scenarios": fixture["scenarios"],
    }
    _validate_wrapper_envelope(synthetic_evidence)

    wrapper_count = 0
    for path in args.wrapper_evidence:
        evidence = _load(path)
        _validate_wrapper_envelope(evidence)
        _validate_scenarios(contract, evidence, operations)
        for scenario in evidence["scenarios"]:
            for event in scenario["events"]:
                _assert(
                    not _forbidden_paths(event["call"]["result"]),
                    f"wrapper result leaks evaluator data in {scenario['fixture_id']}",
                )
        wrapper_count += 1
    print(
        "WS3_TAU_RETAIL_CONTRACT_OK "
        f"version={contract['contract_version']} tools={len(operations)} "
        f"schemas={len(operations) + 4} scenarios={scenarios} calls={calls} "
        f"reset=1 leakage=1 wrapper_evidence={wrapper_count}"
    )


if __name__ == "__main__":
    main()
