#!/usr/bin/env python3
"""Fill private E5 replay hashes with a pinned tau2 retail environment."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import textwrap
import types
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft7Validator


class ReplayError(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode() + payload,
        usedforsecurity=False,
    ).hexdigest()


def verify_source(tau_root: Path, source_version: str) -> None:
    if (tau_root / ".git").exists():
        head = subprocess.run(
            ["git", "-C", str(tau_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    else:
        marker = tau_root / ".tau2-source-commit"
        if not marker.is_file():
            raise ReplayError("tau source has neither .git nor a verified commit marker")
        head = marker.read_text(encoding="utf-8").strip()
    if head != source_version:
        raise ReplayError("tau source does not match the requested pinned version")


def verify_snapshot(
    tau_root: Path,
    snapshot_ref: str,
    expected_blob_sha: str,
) -> Path:
    snapshot = (tau_root / snapshot_ref).resolve()
    try:
        snapshot.relative_to(tau_root.resolve())
    except ValueError as exc:
        raise ReplayError("snapshot path escapes tau root") from exc
    if not snapshot.is_file():
        raise ReplayError("pinned retail snapshot is missing")
    if git_blob_sha(snapshot) != expected_blob_sha:
        raise ReplayError("retail snapshot Git blob does not match the pin")
    return snapshot


def load_tau_environment(tau_root: Path) -> Callable[[], Any]:
    source = tau_root / "src" / "tau2"
    os.environ["TAU2_DATA_DIR"] = str(tau_root / "data")
    names = [
        name
        for name in sys.modules
        if name == "tau2" or name.startswith("tau2.")
    ]
    for name in names:
        del sys.modules[name]
    package = types.ModuleType("tau2")
    package.__path__ = [str(source)]
    sys.modules["tau2"] = package
    from tau2.domains.retail.environment import get_environment

    return get_environment


def load_tasks(tau_root: Path) -> dict[str, dict[str, Any]]:
    path = tau_root / "data" / "tau2" / "domains" / "retail" / "tasks.json"
    tasks = json.loads(path.read_text(encoding="utf-8"))
    return {str(task["id"]): task for task in tasks}


def _source_actions(task: dict[str, Any]) -> dict[str, dict[str, Any]]:
    criteria = task.get("evaluation_criteria") or {}
    return {
        action["action_id"]: action
        for action in (criteria.get("actions") or [])
    }


def structured_user_instructions(task: dict[str, Any]) -> str:
    """Render the exact pinned tau2 StructuredUserInstructions string."""
    try:
        value = task["user_scenario"]["instructions"]
        domain = value["domain"]
        reason = value["reason_for_call"]
        task_instructions = value["task_instructions"]
    except (KeyError, TypeError) as exc:
        raise ReplayError("pinned task lacks structured user instructions") from exc
    if not all(isinstance(item, str) for item in (domain, reason, task_instructions)):
        raise ReplayError("pinned structured user instructions must be strings")
    if any(
        value.get(key) is not None and not isinstance(value[key], str)
        for key in ("known_info", "unknown_info")
    ):
        raise ReplayError("optional structured user instructions must be strings")
    lines = [
        f"Domain: {domain}",
        f"Reason for call:\n{textwrap.indent(reason, chr(9))}",
    ]
    if value.get("known_info") is not None:
        lines.append(f"Known info:\n{textwrap.indent(value['known_info'], chr(9))}")
    if value.get("unknown_info") is not None:
        lines.append(
            f"Unknown info:\n{textwrap.indent(value['unknown_info'], chr(9))}"
        )
    lines.append(
        f"Task instructions:\n{textwrap.indent(task_instructions, chr(9))}"
    )
    return "\n".join(lines)


def _replay_case(
    case: dict[str, Any],
    env_factory: Callable[[], Any],
    tasks: dict[str, dict[str, Any]],
    source_version: str,
    snapshot_ref: str,
    initial_agent_hash: str,
) -> None:
    case_id = case["case_id"]
    task_ref = str(case["source"]["task_ref"])
    if task_ref not in tasks:
        raise ReplayError(f"{case_id}: task_ref is absent from pinned tasks")
    task = tasks[task_ref]
    if task.get("initial_state") is not None:
        raise ReplayError(f"{case_id}: pinned task has a non-default initial state")
    source_actions = _source_actions(task)

    case["user_simulator"]["task_instructions"] = structured_user_instructions(task)
    case["source"]["version"] = source_version
    case["initial_state_ref"] = snapshot_ref
    case["initial_state_hash"] = initial_agent_hash
    env = env_factory()
    for action in case["gold_write_actions"]:
        source_action = source_actions.get(action["action_id"])
        if (
            source_action is None
            or source_action["name"] != action["tool"]
            or source_action["arguments"] != action["arguments"]
        ):
            raise ReplayError(
                f"{case_id}: {action['action_id']} differs from pinned tasks"
            )
        try:
            env.make_tool_call(
                action["tool"],
                requestor="assistant",
                **action["arguments"],
            )
        except Exception as exc:
            raise ReplayError(
                f"{case_id}: {action['action_id']} did not replay cleanly"
            ) from exc

    final_state = case["final_state"]
    final_state["expected_agent_db_hash"] = env.get_db_hash()
    final_state["expected_user_db_hash"] = env.get_user_db_hash()
    final_state["gold_replay_clean"] = True
    if (
        final_state.get("expect_unchanged")
        and final_state["expected_agent_db_hash"] != initial_agent_hash
    ):
        raise ReplayError(f"{case_id}: unchanged case mutated the retail DB")


def fill_replay_fields(
    document: dict[str, Any],
    env_factory: Callable[[], Any],
    tasks: dict[str, dict[str, Any]],
    source_version: str,
    snapshot_ref: str,
) -> dict[str, Any]:
    output = copy.deepcopy(document)
    initial_env = env_factory()
    initial_agent_hash = initial_env.get_db_hash()

    for case in output["cases"]:
        _replay_case(
            case,
            env_factory,
            tasks,
            source_version,
            snapshot_ref,
            initial_agent_hash,
        )

    pending = [
        item.strip()
        for item in str(output.get("pending_fill", "")).split(",")
        if item.strip()
        not in {
            "source.version",
            "initial_state_ref",
            "initial_state_hash",
            "expected_agent_db_hash",
            "expected_user_db_hash",
            "gold_replay_clean",
        }
    ]
    output["pending_fill"] = ", ".join(pending)
    return output


def validate_cases(document: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft7Validator(schema)
    for case in document["cases"]:
        errors = sorted(validator.iter_errors(case), key=lambda error: list(error.path))
        if errors:
            raise ReplayError(
                f"{case['case_id']}: schema validation failed: {errors[0].message}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--tau-root", type=Path, required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--snapshot-ref", required=True)
    parser.add_argument("--snapshot-git-blob", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tau_root = args.tau_root.resolve()
    verify_source(tau_root, args.source_version)
    verify_snapshot(tau_root, args.snapshot_ref, args.snapshot_git_blob)
    document = json.loads(args.batch.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    filled = fill_replay_fields(
        document,
        load_tau_environment(tau_root),
        load_tasks(tau_root),
        args.source_version,
        args.snapshot_ref,
    )
    validate_cases(filled, schema)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(filled, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"E5_REPLAY_OK cases={len(filled['cases'])} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
