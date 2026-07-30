from __future__ import annotations

import json
import os
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
# CrewAI 1.15.1 initializes local trace credential support during import.
# Keep that non-benchmark state in the already ignored project-local directory.
os.environ.setdefault("CREWAI_STORAGE_DIR", str(ROOT / ".crewai"))
if sys.platform == "win32":
    os.environ.setdefault("LOCALAPPDATA", str(ROOT / ".crewai" / "test-appdata"))
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

from adapter.runtime import redact_error
from adapter.schemas import AgentRunResult, BenchmarkTask
from adapter.task_loader import load_task, task_from_dict
from frameworks.crewai_agent import run
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools


class ToolSelectionTests(unittest.TestCase):
    def test_crewai_telemetry_defaults_are_disabled(self) -> None:
        self.assertEqual(os.environ["CREWAI_TRACING_ENABLED"].lower(), "false")
        self.assertEqual(os.environ["CREWAI_DISABLE_TELEMETRY"].lower(), "true")
        self.assertEqual(os.environ["OTEL_SDK_DISABLED"].lower(), "true")

    def test_none_exposes_all_tools_for_vertical(self) -> None:
        selected = run._select_tools("medical_diagnostic", None)
        self.assertEqual([tool.name for tool in selected], ["search_literature"])

    def test_empty_exposes_no_tools(self) -> None:
        self.assertEqual(run._select_tools("medical_diagnostic", []), [])

    def test_one_valid_tool_exposes_only_that_tool(self) -> None:
        selected = run._select_tools(
            "ecommerce_trend_research", ["get_review_history"]
        )
        self.assertEqual([tool.name for tool in selected], ["get_review_history"])

    def test_unknown_tool_exposes_no_tools(self) -> None:
        self.assertEqual(
            run._select_tools("medical_diagnostic", ["unknown_tool"]), []
        )

    def test_wrong_vertical_tool_exposes_no_tools(self) -> None:
        self.assertEqual(
            run._select_tools("medical_diagnostic", ["get_review_history"]), []
        )

    def test_prompt_cannot_grant_a_tool_to_no_tool_task(self) -> None:
        crew_output = SimpleNamespace(token_usage=None)
        fake_crew = Mock()
        fake_crew.kickoff.return_value = crew_output
        with (
            patch.object(run, "Agent", return_value=Mock()) as agent_class,
            patch.object(run, "Task", return_value=Mock()),
            patch.object(run, "Crew", return_value=fake_crew),
        ):
            run._run_agent(
                "You must call search_literature before answering.",
                "medical_diagnostic",
                [],
                Mock(),
            )
        self.assertEqual(agent_class.call_args.kwargs["tools"], [])

    def test_crewai_credential_storage_stays_under_configured_storage(self) -> None:
        from crewai_core.token_manager import TokenManager

        storage_path = TokenManager._get_secure_storage_path()
        configured = Path(os.environ["CREWAI_STORAGE_DIR"]).resolve()
        self.assertTrue(storage_path.is_relative_to(configured))
        self.assertEqual(storage_path.name, "credentials")


class UsageAndConfigurationTests(unittest.TestCase):
    def test_missing_usage_is_safe(self) -> None:
        usage, metadata = run._extract_token_usage(SimpleNamespace(token_usage=None))
        self.assertEqual(
            usage,
            {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        )
        self.assertFalse(metadata["available"])

    def test_crewai_default_zero_usage_is_unavailable(self) -> None:
        metrics = SimpleNamespace(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cached_prompt_tokens=0,
            reasoning_tokens=0,
            cache_creation_tokens=0,
            successful_requests=0,
        )
        usage, metadata = run._extract_token_usage(
            SimpleNamespace(token_usage=metrics)
        )
        self.assertEqual(usage["total_tokens"], None)
        self.assertFalse(metadata["available"])

    def test_zero_usage_without_request_field_is_unavailable(self) -> None:
        metrics = SimpleNamespace(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )
        usage, metadata = run._extract_token_usage(
            SimpleNamespace(token_usage=metrics)
        )
        self.assertIsNone(usage["total_tokens"])
        self.assertFalse(metadata["available"])

    def test_partial_usage_is_normalized(self) -> None:
        metrics = SimpleNamespace(prompt_tokens=12, completion_tokens=3)
        usage, metadata = run._extract_token_usage(
            SimpleNamespace(token_usage=metrics)
        )
        self.assertEqual(
            usage,
            {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15},
        )
        self.assertTrue(metadata["available"])

    def test_error_redaction_preserves_type(self) -> None:
        secret = "sk-unit-test-super-secret"
        with patch.dict(os.environ, {"OPENAI_API_KEY": secret}):
            rendered = redact_error(
                f"RuntimeError: provider rejected {secret}"
            )
        self.assertIn("RuntimeError", rendered)
        self.assertIn("[REDACTED]", rendered)
        self.assertNotIn(secret, rendered)

    def test_error_redaction_removes_url_credentials_and_query_tokens(self) -> None:
        rendered = redact_error(
            "RuntimeError: request "
            "https://user:password@example.test/v1?api_key=secret-value failed"
        )
        self.assertNotIn("user:password", rendered)
        self.assertNotIn("secret-value", rendered)
        self.assertIn("[REDACTED]", rendered)


class CompatibilityAndExecutionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        medical_tools.set_simulate_failure(False)
        ecommerce_tools.set_simulate_failure(False)
        medical_tools.reset_call_log()
        ecommerce_tools.reset_call_log()

    def tearDown(self) -> None:
        medical_tools.set_simulate_failure(False)
        ecommerce_tools.set_simulate_failure(False)

    def _run_with_mocked_boundary(
        self, task: BenchmarkTask, output: str = '{"status":"ok"}'
    ) -> AgentRunResult:
        with patch.object(
            run,
            "_run_agent",
            return_value=(
                output,
                {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
                {
                    "crewai_token_usage": {"available": True, "crew_fields": {}},
                    "selected_tool_names": [],
                },
            ),
        ):
            return run.run_task(task)

    def test_legacy_benchmark_task_and_result_model_compatibility(self) -> None:
        task = load_task(ROOT / "verticals" / "smoke_test" / "task_001.json")
        self.assertIsNone(task.schema_version)
        result = self._run_with_mocked_boundary(task)
        reconstructed = AgentRunResult(**asdict(result))
        self.assertEqual(reconstructed.task_id, task.task_id)
        self.assertIsNone(reconstructed.case_id)
        self.assertEqual(reconstructed.framework, "crewai")

    def test_legacy_empty_allowed_tools_remains_empty(self) -> None:
        task = task_from_dict(
            {
                "task_id": "LEGACY-NO-TOOLS",
                "vertical": "medical_diagnostic",
                "prompt": "Call search_literature.",
                "allowed_tools": [],
            }
        )
        self.assertEqual(task.allowed_tools, [])
        self.assertEqual(run._select_tools(task.vertical, task.allowed_tools), [])

    def test_v1_benchmark_task_and_result_model_compatibility(self) -> None:
        fixtures = json.loads(
            (ROOT / "tests" / "fixtures" / "schema_cases.json").read_text(
                encoding="utf-8"
            )
        )
        document = next(
            fixture["document"]
            for fixture in fixtures["fixtures"]
            if fixture["name"] == "valid_benchmark_case"
        )
        task = task_from_dict(document)
        result = self._run_with_mocked_boundary(task)
        reconstructed = AgentRunResult(**asdict(result))
        self.assertEqual(reconstructed.case_id, "H1-FIXTURE-001")
        self.assertEqual(reconstructed.task_id, "H1")
        self.assertEqual(reconstructed.experiment_id, result.experiment_id)

    def test_no_tool_execution_contract(self) -> None:
        task = BenchmarkTask(
            task_id="NO-TOOL",
            vertical="smoke_test",
            prompt="Return JSON.",
            allowed_tools=[],
        )
        result = self._run_with_mocked_boundary(task)
        self.assertTrue(result.success)
        self.assertEqual(result.tool_call_count, 0)
        self.assertEqual(result.tool_calls, [])

    def test_successful_shared_tool_execution_contract(self) -> None:
        dataset = {
            "21550158": {"CONTEXTS": ["Synthetic abstract for CrewAI testing."]}
        }

        def boundary(*_args, **_kwargs):
            run.search_literature.run(pubmed_id="21550158")
            return (
                '{"status":"ok"}',
                {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
                {"crewai_token_usage": {"available": True, "crew_fields": {}}},
            )

        task = BenchmarkTask(
            task_id="TOOL-SUCCESS",
            vertical="medical_diagnostic",
            prompt="Use the shared fixture.",
            allowed_tools=["search_literature"],
        )
        with (
            patch.object(medical_tools, "_dataset", dataset),
            patch.object(run, "_run_agent", side_effect=boundary),
        ):
            result = run.run_task(task)
        self.assertTrue(result.success)
        self.assertEqual(result.tool_call_count, 1)
        self.assertEqual(result.tool_calls[0]["outcome"], "success")
        self.assertGreaterEqual(result.tool_calls[0]["latency_ms"], 0)

    def test_failed_shared_tool_execution_contract(self) -> None:
        medical_tools.set_simulate_failure(True)

        def boundary(*_args, **_kwargs):
            run.search_literature.run(pubmed_id="21550158")
            raise AssertionError("unreachable")

        task = BenchmarkTask(
            task_id="TOOL-FAILURE",
            vertical="medical_diagnostic",
            prompt="Use the failing shared fixture.",
            allowed_tools=["search_literature"],
        )
        with patch.object(run, "_run_agent", side_effect=boundary):
            result = run.run_task(task)
        self.assertFalse(result.success)
        self.assertEqual(result.tool_call_count, 1)
        self.assertEqual(result.tool_calls[0]["outcome"], "error")
        self.assertIn("RuntimeError", result.error or "")
        self.assertFalse(result.raw_metadata["model_construction_failed"])


if __name__ == "__main__":
    unittest.main()
