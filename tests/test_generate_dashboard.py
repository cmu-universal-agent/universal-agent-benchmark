from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_dashboard


def _row(
    case_id: str,
    label: str,
    note: str,
    framework: str = "langgraph",
) -> dict:
    return {
        "task_id": "E5",
        "case_id": case_id,
        "framework": framework,
        "latency_seconds": 0.1,
        "success": True,
        "error": None,
        "tool_call_count": 1,
        "raw_metadata": {
            "experiment_label": label,
            "runtime_status": "completed",
            "schema_valid": True,
            "final_state_correct": True,
            "note": note,
            "trace": [
                {
                    "index": 0,
                    "tool_name": "get_order_details",
                    "arguments": {"order_id": "PRIVATE-ORDER"},
                    "ok": True,
                    "state_changed": False,
                    "result": {"private": "PRIVATE-RESULT"},
                    "state_before_sha256": "a" * 64,
                    "state_after_sha256": "b" * 64,
                }
            ],
            "final_state": {"private": "PRIVATE-ACTUAL-STATE"},
            "expected_state": {"private": "PRIVATE-GOLD-STATE"},
            "evaluator_output": {"private": "PRIVATE-EVALUATION"},
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
        rows[0]["raw_metadata"]["final_state_correct"] = False
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
            keyed[("RETAIL-E5-001", "langgraph", "pilot")][
                "final_state_verdict"
            ],
            "correct",
        )
        self.assertIn(("RETAIL-E5-002", "langgraph", "pilot"), keyed)
        self.assertIn(
            ("RETAIL-E5-001", "langgraph", "technical_smoke"),
            keyed,
        )

        html = generate_dashboard.render_html(payload)
        self.assertIn(
            "runByDomKey[runDomKey(r.case_id, r.framework, r.experiment_label)]",
            html,
        )
        self.assertIn(
            "const lookupKey = runDomKey(c.id, f.id, state.label);",
            html,
        )
        self.assertIn(
            "const domKey = runDomKey(r.case_id, r.framework, r.experiment_label);",
            html,
        )
        self.assertIn('data-run="${esc(domKey)}"', html)
        self.assertIn("const r = runByDomKey[domKey];", html)

    def test_public_payload_is_allowlisted_and_private_values_are_absent(self) -> None:
        rows = [
            _row("RETAIL-E5-001", "technical_smoke", "PRIVATE-EVALUATOR-NOTE"),
            _row(
                "RETAIL-E5-001",
                "technical_smoke",
                "PRIVATE-CREWAI-NOTE",
                framework="crewai",
            ),
        ]
        with patch.object(
            generate_dashboard,
            "_load_latest_dashboard_results",
            return_value=rows,
        ):
            payload = generate_dashboard.build_payload("retail")
        html = generate_dashboard.render_html(payload)

        self.assertEqual(
            [run["framework"] for run in payload["runs"]],
            ["langgraph"],
        )
        self.assertEqual(
            payload["runs"][0]["trace"],
            [
                {
                    "index": 0,
                    "tool_name": "get_order_details",
                    "outcome": "ok",
                    "state_changed": False,
                }
            ],
        )
        for private_value in (
            "PRIVATE-ORDER",
            "PRIVATE-RESULT",
            "PRIVATE-ACTUAL-STATE",
            "PRIVATE-GOLD-STATE",
            "PRIVATE-EVALUATION",
            "PRIVATE-EVALUATOR-NOTE",
            "PRIVATE-CREWAI-NOTE",
            "a" * 64,
            "b" * 64,
        ):
            self.assertNotIn(private_value, html)
        self.assertNotIn('"expected_state"', html)
        self.assertNotIn('"arguments"', html)

    def test_framework_cards_show_evidence_availability_not_scores(self) -> None:
        with patch.object(
            generate_dashboard,
            "_load_latest_dashboard_results",
            return_value=[
                _row("RETAIL-E5-001", "technical_smoke", "available")
            ],
        ):
            payload = generate_dashboard.build_payload("retail")
        by_id = {
            framework["id"]: framework
            for framework in payload["frameworks"]
        }
        html = generate_dashboard.render_html(payload)

        self.assertEqual(by_id["langgraph"]["evidence_status"], "available")
        self.assertEqual(
            by_id["openai_agents_sdk"]["evidence_status"],
            "available",
        )
        self.assertEqual(by_id["crewai"]["evidence_status"], "not_available")
        self.assertIn("SYNTHETIC TECHNICAL VALIDATION", html)
        self.assertIn("NOT BENCHMARK SCORES", html)
        self.assertIn("no simulated ranking", html)
        self.assertNotIn("Pass rate", html)
        self.assertNotIn("Median latency", html)

    def test_synthetic_walkthrough_is_populated_and_public_safe(self) -> None:
        with patch.object(
            generate_dashboard,
            "_load_latest_dashboard_results",
            return_value=[],
        ):
            payload = generate_dashboard.build_payload(
                "retail",
                include_synthetic_walkthrough=True,
            )
        html = generate_dashboard.render_html(payload)
        walkthrough = payload["synthetic_walkthrough"]

        self.assertEqual(walkthrough["case_id"], "RETAIL-E5-001")
        self.assertEqual(walkthrough["allowed_tools"], 16)
        self.assertIn("customer contacts support", walkthrough["input_summary"])
        self.assertIn("get_order_details", html)
        self.assertIn("modify_pending_order_payment", html)
        self.assertIn("not an agent answer", html)
        for forbidden in (
            "state_before_sha256",
            "state_after_sha256",
            '"arguments"',
            '"expected_state"',
            '"evaluator_output"',
            "PRIVATE-",
        ):
            self.assertNotIn(forbidden, html)

if __name__ == "__main__":
    unittest.main()
