from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from adapter.schemas import AgentRunResult
from frameworks.crewai_agent.check_results import inspect_rows


def _result(case_id: str, success: bool = True) -> AgentRunResult:
    return AgentRunResult(
        task_id="SMOKE-001",
        case_id=case_id,
        framework="crewai",
        vertical="smoke_test",
        final_output='{"status":"completed"}' if success else "",
        latency_seconds=0.1,
        success=success,
        error=None if success else "RuntimeError: synthetic",
        tool_call_count=0,
        run_id=f"run-{case_id.lower()}",
        experiment_id="exp-test",
        framework_version="1.15.1",
        model_provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.0,
        prompt_version="test-v1",
        started_at="2026-07-20T00:00:00+00:00",
        completed_at="2026-07-20T00:00:01+00:00",
        raw_output='{"status":"completed"}' if success else "",
        token_usage={"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
    )


class CrewAIResultCheckerTests(unittest.TestCase):
    def test_valid_rows_are_reconstructed_and_summarized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(asdict(_result("CASE-001"))) + "\n", encoding="utf-8")
            summary, errors = inspect_rows([path])
        self.assertEqual(errors, [])
        self.assertEqual(summary["rows"], 1)
        self.assertEqual(summary["success"], 1)
        self.assertEqual(summary["task_counts"]["SMOKE-001"], 1)
        self.assertEqual(summary["malformed_outputs"], [])

    def test_duplicate_case_ids_and_malformed_outputs_are_reported(self) -> None:
        first = _result("CASE-001")
        second = _result("CASE-001", success=False)
        second.run_id = "run-second"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(
                "\n".join((json.dumps(asdict(first)), json.dumps(asdict(second)))) + "\n",
                encoding="utf-8",
            )
            summary, errors = inspect_rows([path])
        self.assertEqual(summary["duplicate_case_ids"], ["CASE-001"])
        self.assertEqual(summary["malformed_outputs"], [])
        self.assertTrue(any("duplicate case IDs" in error for error in errors))

    def test_same_case_id_in_different_experiments_is_not_duplicate(self) -> None:
        first = _result("CASE-001")
        second = _result("CASE-001")
        second.run_id = "run-second"
        second.experiment_id = "exp-second"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(
                "\n".join((json.dumps(asdict(first)), json.dumps(asdict(second)))) + "\n",
                encoding="utf-8",
            )
            summary, errors = inspect_rows([path])
        self.assertEqual(summary["duplicate_case_ids"], [])
        self.assertEqual(errors, [])

    def test_successful_malformed_output_is_a_validation_error(self) -> None:
        row = asdict(_result("CASE-001"))
        row["final_output"] = "not json"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            summary, errors = inspect_rows([path])
        self.assertEqual(len(summary["malformed_outputs"]), 1)
        self.assertTrue(any("malformed final output" in error for error in errors))

    def test_invalid_success_type_is_not_counted_as_failure(self) -> None:
        row = asdict(_result("CASE-001"))
        row["success"] = "true"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            summary, errors = inspect_rows([path])
        self.assertEqual(summary["success"], 0)
        self.assertEqual(summary["failure"], 0)
        self.assertTrue(any("success must be a boolean" in error for error in errors))

    def test_bad_task_id_type_does_not_abort_later_rows(self) -> None:
        malformed = asdict(_result("CASE-001"))
        malformed["task_id"] = []
        valid = asdict(_result("CASE-002"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(
                "\n".join((json.dumps(malformed), json.dumps(valid))) + "\n",
                encoding="utf-8",
            )
            summary, errors = inspect_rows([path])
        self.assertEqual(summary["rows"], 2)
        self.assertEqual(summary["task_counts"]["SMOKE-001"], 1)
        self.assertTrue(any("task_id must be a string" in error for error in errors))

    def test_tool_calls_are_checked_against_shared_schema(self) -> None:
        row = asdict(_result("CASE-001"))
        row["tool_call_count"] = 1
        row["tool_calls"] = [{}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            _summary, errors = inspect_rows([path])
        self.assertTrue(any("tool_calls[0] schema" in error for error in errors))

    def test_non_model_fields_are_rejected(self) -> None:
        row = asdict(_result("CASE-001"))
        row["unexpected"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            summary, errors = inspect_rows([path])
        self.assertEqual(summary["rows"], 0)
        self.assertTrue(any("AgentRunResult rejected row" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
