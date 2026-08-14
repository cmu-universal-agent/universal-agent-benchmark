import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from adapter import result_writer


class ResultWriterTests(unittest.TestCase):
    def test_latest_attempt_keeps_distinct_cases_and_repeats(self):
        common = {
            "task_id": "E5",
            "framework": "fw",
            "experiment_id": "exp",
            "model_name": "model",
        }
        rows = [
            {**common, "case_id": "E5-001", "logical_run_id": "repeat-1", "attempt": 1},
            {**common, "case_id": "E5-001", "logical_run_id": "repeat-1", "attempt": 2},
            {**common, "case_id": "E5-001", "logical_run_id": "repeat-2", "attempt": 1},
            {**common, "case_id": "E5-002", "logical_run_id": "repeat-1", "attempt": 1},
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            with patch.object(result_writer, "default_result_path", return_value=path):
                latest = result_writer.load_latest_results("retail", model_name="model")

        self.assertEqual(len(latest), 3)
        self.assertEqual(
            latest[("E5-001", "fw", "exp", "repeat-1")]["attempt"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
