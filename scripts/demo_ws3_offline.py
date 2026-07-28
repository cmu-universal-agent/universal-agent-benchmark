#!/usr/bin/env python3
"""Run a deterministic contract-only WS3 demo with synthetic evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import validate_ws3_tau_retail_contract as validator  # noqa: E402


def run_demo(evidence_out: Path | None = None) -> dict[str, Any]:
    contract = validator._load(validator.CONTRACT_PATH)
    fixture = validator._load(validator.FIXTURE_PATH)
    operations = validator._validate_registry(contract, fixture)
    scenarios, calls = validator._validate_scenarios(
        contract, fixture, operations
    )
    validator._validate_leakage(fixture)

    evidence = {
        "contract_version": contract["contract_version"],
        "framework": "langgraph",
        "wrapper_version": "synthetic-contract-fixture",
        "generated_at": "2026-07-22T00:00:00Z",
        "reset_determinism": fixture["reset_determinism"],
        "scenarios": fixture["scenarios"],
    }
    validator._validate_wrapper_envelope(evidence)

    by_id = {row["fixture_id"]: row for row in fixture["scenarios"]}
    read = by_id["read_success"]
    write = by_id["write_success"]
    duplicate = by_id["duplicate_action"]
    summary = {
        "version": contract["contract_version"],
        "tools": len(operations),
        "scenarios": scenarios,
        "calls": calls,
        "reset_deterministic": (
            fixture["reset_determinism"]["first"]["state_sha256"]
            == fixture["reset_determinism"]["second"]["state_sha256"]
        ),
        "read_tool": read["events"][0]["call"]["tool_name"],
        "read_state_changed": (
            read["events"][0]["state_before_sha256"]
            != read["events"][0]["state_after_sha256"]
        ),
        "write_tool": write["events"][0]["call"]["tool_name"],
        "write_mutation_count": write["final_state"]["mutation_count"],
        "duplicate_tool": duplicate["events"][-1]["call"]["tool_name"],
        "duplicate_error": duplicate["events"][-1]["call"]["error"]["error_type"],
        "duplicate_state_changed": (
            duplicate["events"][-1]["state_before_sha256"]
            != duplicate["events"][-1]["state_after_sha256"]
        ),
        "leakage": 0,
    }

    if evidence_out is not None:
        evidence_out.parent.mkdir(parents=True, exist_ok=True)
        evidence_out.write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-out",
        type=Path,
        help="Optional path for sanitized synthetic evidence JSON.",
    )
    args = parser.parse_args()
    summary = run_demo(args.evidence_out)
    print("WS3_OFFLINE_DEMO technical_validation_only=1 benchmark_scores=0")
    print(
        f"CONTRACT_OK version={summary['version']} tools={summary['tools']}"
    )
    print(f"RESET_OK deterministic={int(summary['reset_deterministic'])}")
    print(
        f"READ_OK tool={summary['read_tool']} "
        f"state_changed={int(summary['read_state_changed'])}"
    )
    print(
        f"WRITE_OK tool={summary['write_tool']} "
        f"mutation_count={summary['write_mutation_count']}"
    )
    print(
        f"DUPLICATE_OK tool={summary['duplicate_tool']} "
        f"error={summary['duplicate_error']} "
        f"state_changed={int(summary['duplicate_state_changed'])}"
    )
    print(
        f"EVIDENCE_OK scenarios={summary['scenarios']} "
        f"calls={summary['calls']} leakage={summary['leakage']}"
    )
    if args.evidence_out is not None:
        print(f"EVIDENCE_FILE path={args.evidence_out}")


if __name__ == "__main__":
    main()
