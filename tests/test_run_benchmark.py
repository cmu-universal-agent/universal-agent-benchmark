import json
import os
import subprocess
import sys
import unittest
from subprocess import TimeoutExpired
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.run_benchmark import (
    _append_attempt,
    _attempt_result_rows,
    _load_gold,
    _next_attempt,
    _repeat_numbers,
    _require_session_runs,
    _run_framework_process,
)


class RunBenchmarkTests(unittest.TestCase):
    def test_exact_repeat_selection_skips_earlier_repeats(self):
        self.assertEqual(_repeat_numbers(3, 2), [2])
        self.assertEqual(_repeat_numbers(3, None), [1, 2, 3])

    def test_help_runs_without_site_packages(self):
        completed = subprocess.run(
            [sys.executable, "-S", "scripts/run_benchmark.py", "--help"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_single_case_loads_sibling_gold(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / "cases" / "task_E5-001.json"
            gold = root / "gold" / "E5.jsonl"
            case.parent.mkdir()
            gold.parent.mkdir()
            case.write_text("{}", encoding="utf-8")
            gold.write_text(
                json.dumps({"case_id": "E5-001", "gold": {}}) + "\n",
                encoding="utf-8",
            )

            self.assertIn("E5-001", _load_gold(case))

    def test_single_case_prefers_configured_versioned_e5_gold(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / "cases" / "task_E5-001.json"
            gold = root / "pilot-60-v1.3" / "E5.jsonl"
            case.parent.mkdir()
            gold.parent.mkdir()
            case.write_text("{}", encoding="utf-8")
            gold.write_text(
                json.dumps({"case_id": "E5-001", "gold": {"version": "v1.3"}})
                + "\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"BENCHMARK_E5_GOLD_PATH": str(gold)},
                clear=False,
            ):
                loaded = _load_gold(case)

            self.assertEqual(loaded["E5-001"]["gold"]["version"], "v1.3")

    def test_missing_current_experiment_row_cannot_fall_back_to_old_result(self):
        with self.assertRaisesRegex(RuntimeError, "found 0"):
            _require_session_runs(
                [],
                expected=1,
                case_key="H1-001",
                framework="openai_agents_sdk",
            )

    def test_rerun_requires_reason_and_stops_after_one_retry(self):
        with TemporaryDirectory() as directory:
            ledger = Path(directory) / "attempts.jsonl"
            record = {"logical_run_id": "exp:H1:framework:repeat-1"}
            _append_attempt(ledger, record)
            with self.assertRaisesRegex(RuntimeError, "rerun reason required"):
                _next_attempt(ledger, record["logical_run_id"], None)
            self.assertEqual(
                _next_attempt(ledger, record["logical_run_id"], "provider error"),
                2,
            )
            _append_attempt(ledger, record)
            with self.assertRaisesRegex(RuntimeError, "rerun limit reached"):
                _next_attempt(ledger, record["logical_run_id"], "provider error")

    def test_result_rows_join_on_logical_run_and_attempt(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(
                "\n".join(
                    [
                        '{"logical_run_id":"logical-1","attempt":1,"run_id":"run-1"}',
                        '{"logical_run_id":"logical-1","attempt":2,"run_id":"run-2"}',
                        '{"logical_run_id":"logical-2","attempt":1,"run_id":"run-3"}',
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                _attempt_result_rows(
                    path,
                    logical_run_id="logical-1",
                    attempt=2,
                ),
                [
                    {
                        "logical_run_id": "logical-1",
                        "attempt": 2,
                        "run_id": "run-2",
                    }
                ],
            )

    @patch("scripts.run_benchmark._terminate_process_tree")
    @patch("scripts.run_benchmark.subprocess.Popen")
    def test_timeout_terminates_framework_process_tree(self, popen, terminate):
        process = popen.return_value
        process.wait.side_effect = TimeoutExpired("framework", 300)

        with self.assertRaises(TimeoutExpired):
            _run_framework_process(["python", "run.py"], env={}, timeout=300)

        terminate.assert_called_once_with(process)


if __name__ == "__main__":
    unittest.main()
