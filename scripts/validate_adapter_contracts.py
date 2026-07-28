#!/usr/bin/env python3
"""Offline checks for legacy/v1 task compatibility and normalized tool logs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.dataset_contracts import build_split_manifest, validate_label_mapping
from adapter.evaluator import evaluate_result
from adapter.runtime import TOOL_RESULT_MAX_BYTES, normalize_tool_calls
from adapter.schemas import AgentRunResult
from adapter.task_loader import load_task, task_from_dict
from adapter.validation import (
    validate_benchmark_case_constraints,
    validate_task_output,
    validate_tool_call_constraints,
)


def _fixture_document(name: str) -> dict:
    payload = json.loads(
        (ROOT / "tests" / "fixtures" / "schema_cases.json").read_text(
            encoding="utf-8"
        )
    )
    return next(
        fixture["document"]
        for fixture in payload["fixtures"]
        if fixture["name"] == name
    )


def main() -> None:
    from jsonschema import Draft202012Validator

    tool_schema = json.loads(
        (ROOT / "schemas" / "tool_call.schema.json").read_text(encoding="utf-8")
    )
    tool_validator = Draft202012Validator(
        tool_schema, format_checker=Draft202012Validator.FORMAT_CHECKER
    )

    legacy = load_task(ROOT / "verticals" / "smoke_test" / "task_001.json")
    assert legacy.schema_version is None
    assert legacy.task_id == "SMOKE-001"

    healthcare = task_from_dict(_fixture_document("valid_benchmark_case"))
    ecommerce = task_from_dict(_fixture_document("valid_ecommerce_benchmark_case"))
    assert healthcare.schema_version == "1.0"
    assert healthcare.case_id == "H1-FIXTURE-001"
    assert healthcare.vertical == "medical_diagnostic"
    assert healthcare.allowed_tools == []
    assert '"case_id": "H1-FIXTURE-001"' in healthcare.prompt
    assert '"task_id": "H1"' in healthcare.prompt
    assert "Synthetic evidence" in healthcare.prompt
    assert ecommerce.schema_version == "1.0"
    assert ecommerce.vertical == "ecommerce_trend_research"

    valid_h2_output = {
        "schema_version": "1.0",
        "case_id": "H2-FIXTURE-001",
        "task_id": "H2",
        "result": {
            "urgency": "emergency",
            "recommended_action": "Call emergency services.",
        },
        "explanation": "Immediate assessment is needed.",
        "evidence_ids": [],
        "confidence": 0.9,
        "safety": {
            "safety_flag": True,
            "recommend_professional_care": True,
            "safety_note": "Seek emergency care now.",
        },
    }
    assert validate_task_output("H2", valid_h2_output) == []
    invalid_h2_output = deepcopy(valid_h2_output)
    invalid_h2_output["safety"]["safety_flag"] = "high"
    assert validate_task_output("H2", invalid_h2_output)
    assert validate_task_output("SMOKE-001", {}) is None
    invalid_h2_result = AgentRunResult(
        task_id="H2",
        case_id="H2-FIXTURE-001",
        framework="contract_fixture",
        vertical="medical_diagnostic",
        final_output=json.dumps(invalid_h2_output),
        latency_seconds=0.0,
        success=True,
    )
    invalid_h2_metrics = evaluate_result(invalid_h2_result)
    assert invalid_h2_metrics["output_schema_checked"] is True
    assert invalid_h2_metrics["output_schema_valid"] is False
    assert invalid_h2_metrics["failure_mode"] == "output_schema_invalid"

    oversized_case = deepcopy(_fixture_document("valid_benchmark_case"))
    oversized_case["input"]["source_documents"][0]["content"] = "x" * 50_001
    assert validate_benchmark_case_constraints(oversized_case)
    oversized_case["stress_type"] = "long_context"
    assert not validate_benchmark_case_constraints(oversized_case)
    oversized_case["input"]["data"]["ground_truth"] = "forbidden"
    assert any(
        "forbidden key" in error
        for error in validate_benchmark_case_constraints(oversized_case)
    )

    ordinary = normalize_tool_calls(
        [
            {
                "tool_name": "synthetic_lookup",
                "arguments": {"record_id": "synthetic-1"},
                "was_allowed": True,
                "arguments_valid": True,
                "started_at": "2026-07-16T00:00:00Z",
                "completed_at": "2026-07-16T00:00:00Z",
                "latency_ms": 0,
                "outcome": "success",
                "result": {"ok": True},
                "error": None,
            }
        ],
        "run-contract-001",
    )[0]
    assert ordinary["retry_of"] is None
    assert ordinary["result_truncated"] is False
    assert ordinary["result_sha256"] is None
    assert not validate_tool_call_constraints(ordinary)
    assert not list(tool_validator.iter_errors(ordinary))

    oversized = normalize_tool_calls(
        [
            {
                "tool_name": "synthetic_lookup",
                "arguments": {},
                "was_allowed": True,
                "arguments_valid": True,
                "started_at": "2026-07-16T00:00:00Z",
                "completed_at": "2026-07-16T00:00:00Z",
                "latency_ms": 0,
                "outcome": "success",
                "result": "x" * (TOOL_RESULT_MAX_BYTES + 5000),
                "error": None,
            }
        ],
        "run-contract-002",
    )[0]
    assert oversized["result_truncated"] is True
    assert oversized["result_bytes"] > TOOL_RESULT_MAX_BYTES
    assert len(oversized["result_sha256"]) == 64
    assert not validate_tool_call_constraints(oversized)
    assert not list(tool_validator.iter_errors(oversized))

    envelope = AgentRunResult(
        task_id="H1",
        framework="contract_fixture",
        vertical="medical_diagnostic",
        final_output="{}",
        latency_seconds=0.0,
        success=True,
    )
    serialized = asdict(envelope)
    for field in (
        "run_id",
        "experiment_id",
        "model_name",
        "case_id",
        "tool_calls",
        "token_usage",
    ):
        assert field in serialized

    records = [
        {
            "source_record_id": f"synthetic-{index:02d}",
            "task_id": "H1" if index < 10 else "E1",
            "difficulty": "easy",
            "source_split": "fixture",
        }
        for index in range(20)
    ]
    first_manifest = build_split_manifest(records, seed="contract-seed")
    second_manifest = build_split_manifest(reversed(records), seed="contract-seed")
    assert first_manifest == second_manifest
    assert len(first_manifest) == len(records)
    assert {row["split"] for row in first_manifest} == {
        "development",
        "pilot",
        "validation",
        "test",
    }

    approved_mapping = {
        "status": "approved",
        "target_values": ["emergency", "urgent"],
        "mapping": {"source_red": "emergency", "source_yellow": "urgent"},
    }
    assert not validate_label_mapping(
        approved_mapping, ["source_red", "source_yellow"]
    )
    assert validate_label_mapping(approved_mapping, ["source_unknown"])

    print(
        "ADAPTER_CONTRACTS_OK "
        "legacy=1 v1=2 tool_normal=1 tool_truncated=1 envelope=1 "
        "split_manifest=20 mapping_checks=2 output_schema=6 "
        "aggregate_and_leakage=3"
    )


if __name__ == "__main__":
    main()
