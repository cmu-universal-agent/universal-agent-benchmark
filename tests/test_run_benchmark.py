import json
import os
import unittest
from subprocess import TimeoutExpired
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.run_benchmark import (
    _append_attempt,
    _load_gold,
    _next_attempt,
    _require_session_runs,
    _result_count,
    _run_framework_process,
)


class RunBenchmarkTests(unittest.TestCase):
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

    def test_result_count_is_scoped_to_logical_run(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(
                "\n".join(
                    [
                        '{"experiment_id":"old","case_id":"H1","framework":"fw"}',
                        '{"experiment_id":"exp","case_id":"H1","framework":"fw"}',
                        '{"experiment_id":"exp","case_id":"H2","framework":"fw"}',
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                _result_count(
                    path,
                    experiment_id="exp",
                    case_key="H1",
                    framework="fw",
                ),
                1,
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
