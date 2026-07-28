from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("CREWAI_STORAGE_DIR", str(ROOT / ".crewai"))
if sys.platform == "win32":
    os.environ.setdefault("LOCALAPPDATA", str(ROOT / ".crewai" / "test-appdata"))
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

from adapter.schemas import AgentRunResult
from frameworks.crewai_agent import run_core


def _case(case_id: str, task_id: str, vertical: str) -> dict:
    return {
        "schema_version": "1.0",
        "case_id": case_id,
        "task_id": task_id,
        "vertical": vertical,
        "input": {"instruction": "Return one JSON object.", "data": {"value": 1}},
        "allowed_tools": [],
        "stress_type": "standard",
        "metadata": {
            "dataset": "synthetic",
            "split": "pilot",
            "difficulty": "easy",
            "language": "en",
        },
    }


class CrewAICoreRunnerTests(unittest.TestCase):
    def test_list_only_accepts_all_eight_core_task_entries(self) -> None:
        vertical_by_task = {
            "H1": "healthcare",
            "H2": "healthcare",
            "H4": "healthcare",
            "H5": "healthcare",
            "E1": "ecommerce",
            "E2": "ecommerce",
            "E3": "ecommerce",
            "E5": "ecommerce",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (task_id, vertical) in enumerate(vertical_by_task.items(), 1):
                (root / f"task_{index:02d}.json").write_text(
                    json.dumps(_case(f"{task_id}-TEST-001", task_id, vertical)),
                    encoding="utf-8",
                )
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    ["run_core.py", "--task", str(root), "--list-only"],
                ),
                patch.object(run_core, "run_task") as run_task,
                patch.object(run_core, "append_result") as append_result,
                redirect_stdout(output),
            ):
                exit_code = run_core.main()
        self.assertEqual(exit_code, 0)
        self.assertIn(
            "DISCOVERY_COUNTS H1=1 H2=1 H4=1 H5=1 E1=1 E2=1 E3=1 E5=1",
            output.getvalue(),
        )
        run_task.assert_not_called()
        append_result.assert_not_called()

    def test_discovery_accepts_directory_and_orders_core_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "task_z.json").write_text(
                json.dumps(_case("E5-TEST-002", "E5", "ecommerce")),
                encoding="utf-8",
            )
            (root / "task_a.json").write_text(
                json.dumps(_case("H1-TEST-001", "H1", "healthcare")),
                encoding="utf-8",
            )
            cases, errors = run_core.discover_cases(root)
        self.assertEqual(errors, [])
        self.assertEqual([item.task.task_id for item in cases], ["H1", "E5"])
        self.assertEqual(
            [item.task.case_id for item in cases], ["H1-TEST-001", "E5-TEST-002"]
        )

    def test_discovery_accepts_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one.json"
            path.write_text(
                json.dumps(_case("H2-TEST-001", "H2", "healthcare")),
                encoding="utf-8",
            )
            cases, errors = run_core.discover_cases(path)
        self.assertEqual(errors, [])
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].task.case_id, "H2-TEST-001")

    def test_dry_run_discovers_without_execution_or_result_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one.json"
            path.write_text(
                json.dumps(_case("H2-TEST-001", "H2", "healthcare")),
                encoding="utf-8",
            )
            with (
                patch.object(sys, "argv", ["run_core.py", "--task", str(path), "--dry-run"]),
                patch.object(run_core, "run_task") as run_task,
                patch.object(run_core, "append_result") as append_result,
            ):
                exit_code = run_core.main()
        self.assertEqual(exit_code, 0)
        run_task.assert_not_called()
        append_result.assert_not_called()

    def test_runner_continues_after_individual_setup_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in (1, 2):
                (root / f"task_{index}.json").write_text(
                    json.dumps(_case(f"H1-TEST-00{index}", "H1", "healthcare")),
                    encoding="utf-8",
                )
            successful_result = AgentRunResult(
                task_id="H1",
                case_id="H1-TEST-002",
                framework="crewai",
                vertical="medical_diagnostic",
                final_output="{}",
                latency_seconds=0.01,
                success=True,
                run_id="run-test-002",
                experiment_id="exp-test",
            )
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "run_core.py",
                        "--task",
                        str(root),
                        "--experiment-id",
                        "exp-test",
                    ],
                ),
                patch.object(
                    run_core,
                    "run_task",
                    side_effect=[RuntimeError("synthetic setup error"), successful_result],
                ) as run_task,
                patch.object(run_core, "append_result") as append_result,
            ):
                exit_code = run_core.main()
        self.assertEqual(exit_code, 1)
        self.assertEqual(run_task.call_count, 2)
        append_result.assert_called_once_with(successful_result, None)

    def test_runner_returns_failure_when_a_completed_case_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.json"
            path.write_text(
                json.dumps(_case("H1-TEST-001", "H1", "healthcare")),
                encoding="utf-8",
            )
            failed_result = AgentRunResult(
                task_id="H1",
                case_id="H1-TEST-001",
                framework="crewai",
                vertical="medical_diagnostic",
                final_output="",
                latency_seconds=0.01,
                success=False,
                error="RuntimeError: synthetic",
                run_id="run-test-001",
                experiment_id="exp-test",
            )
            with (
                patch.object(
                    sys,
                    "argv",
                    ["run_core.py", "--task", str(path), "--experiment-id", "exp-test"],
                ),
                patch.object(run_core, "run_task", return_value=failed_result),
                patch.object(run_core, "append_result") as append_result,
            ):
                exit_code = run_core.main()
        self.assertEqual(exit_code, 1)
        append_result.assert_called_once_with(failed_result, None)


if __name__ == "__main__":
    unittest.main()
