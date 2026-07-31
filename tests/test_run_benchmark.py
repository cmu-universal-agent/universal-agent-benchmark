import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.run_benchmark import (
    _append_attempt,
    _next_attempt,
    _require_session_runs,
    _result_count,
)


class RunBenchmarkTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
