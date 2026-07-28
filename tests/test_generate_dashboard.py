from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_dashboard


def _row(case_id: str, label: str, note: str) -> dict:
    return {
        "task_id": "E5",
        "case_id": case_id,
        "framework": "crewai",
        "latency_seconds": 0.1,
        "success": True,
        "error": None,
        "tool_call_count": 1,
        "raw_metadata": {
            "experiment_label": label,
            "note": note,
        },
    }


class GenerateDashboardTests(unittest.TestCase):
    def test_latest_rows_are_kept_per_case_framework_and_label(self) -> None:
        rows = [
            _row("RETAIL-E5-001", "pilot", "old"),
            _row("RETAIL-E5-002", "pilot", "second case"),
            _row("RETAIL-E5-001", "pilot", "latest"),
            _row("RETAIL-E5-001", "technical_smoke", "other label"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "retail_results.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            with patch.object(
                generate_dashboard,
                "default_result_path",
                return_value=path,
            ):
                payload = generate_dashboard.build_payload("retail")

        keyed = {
            (run["case_id"], run["framework"], run["experiment_label"]): run
            for run in payload["runs"]
        }
        self.assertEqual(len(keyed), 3)
        self.assertEqual(
            keyed[("RETAIL-E5-001", "crewai", "pilot")]["note"],
            "latest",
        )
        self.assertIn(("RETAIL-E5-002", "crewai", "pilot"), keyed)
        self.assertIn(
            ("RETAIL-E5-001", "crewai", "technical_smoke"),
            keyed,
        )


if __name__ == "__main__":
    unittest.main()
