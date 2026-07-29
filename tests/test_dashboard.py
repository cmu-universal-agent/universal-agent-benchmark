import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapter import result_writer
from scripts import generate_dashboard


def _row(
    *,
    task_id: str = "RETAIL-E5-001",
    framework: str = "langgraph",
    label: str = "technical_smoke",
    marker: str = "marker",
) -> dict:
    return {
        "task_id": task_id,
        "framework": framework,
        "vertical": "retail",
        "final_output": "{}",
        "latency_seconds": 1.0,
        "success": True,
        "error": None,
        "tool_call_count": 1,
        "raw_metadata": {
            "experiment_label": label,
            "runtime_status": "completed",
            "schema_valid": True,
            "final_state_correct": True,
            "marker": marker,
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
            "note": "PRIVATE-EVALUATOR-NOTE",
        },
    }


class ResultLoaderLabelTests(unittest.TestCase):
    def test_latest_results_keeps_same_case_framework_for_both_labels(self):
        rows = [
            _row(label="technical_smoke", marker="smoke-old"),
            _row(label="pilot", marker="pilot"),
            _row(label="technical_smoke", marker="smoke-new"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "retail_results.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            with mock.patch.object(result_writer, "default_result_path", return_value=path):
                latest = result_writer.load_latest_results("retail")

        self.assertEqual(
            set(latest),
            {
                ("RETAIL-E5-001", "langgraph", "technical_smoke"),
                ("RETAIL-E5-001", "langgraph", "pilot"),
            },
        )
        self.assertEqual(
            latest[
                ("RETAIL-E5-001", "langgraph", "technical_smoke")
            ]["raw_metadata"]["marker"],
            "smoke-new",
        )
        self.assertEqual(
            latest[("RETAIL-E5-001", "langgraph", "pilot")]["raw_metadata"][
                "marker"
            ],
            "pilot",
        )


class DashboardGenerationTests(unittest.TestCase):
    def test_double_label_rows_survive_payload_and_use_triple_dom_key(self):
        smoke = _row(label="technical_smoke")
        pilot = _row(label="pilot")
        latest = {
            ("RETAIL-E5-001", "langgraph", "technical_smoke"): smoke,
            ("RETAIL-E5-001", "langgraph", "pilot"): pilot,
        }
        with mock.patch.object(
            generate_dashboard, "load_latest_results", return_value=latest
        ):
            payload = generate_dashboard.build_payload("retail")
        html = generate_dashboard.render_html(payload)

        self.assertEqual(len(payload["runs"]), 2)
        self.assertEqual(
            {run["experiment_label"] for run in payload["runs"]},
            {"technical_smoke", "pilot"},
        )
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

    def test_public_payload_is_allowlisted_and_private_values_are_absent(self):
        langgraph = _row(framework="langgraph")
        crewai = _row(framework="crewai")
        latest = {
            ("RETAIL-E5-001", "langgraph", "technical_smoke"): langgraph,
            ("RETAIL-E5-001", "crewai", "technical_smoke"): crewai,
        }
        with mock.patch.object(
            generate_dashboard, "load_latest_results", return_value=latest
        ):
            payload = generate_dashboard.build_payload("retail")
        html = generate_dashboard.render_html(payload)

        self.assertEqual([run["framework"] for run in payload["runs"]], ["langgraph"])
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
        self.assertEqual(payload["runs"][0]["final_state_verdict"], "correct")

        for private_value in (
            "PRIVATE-ORDER",
            "PRIVATE-RESULT",
            "PRIVATE-ACTUAL-STATE",
            "PRIVATE-GOLD-STATE",
            "PRIVATE-EVALUATION",
            "PRIVATE-EVALUATOR-NOTE",
            "a" * 64,
            "b" * 64,
        ):
            self.assertNotIn(private_value, html)
        self.assertNotIn('"expected_state"', html)
        self.assertNotIn('"arguments"', html)

    def test_framework_cards_are_evidence_availability_not_scores(self):
        with mock.patch.object(
            generate_dashboard,
            "load_latest_results",
            return_value={
                (
                    "RETAIL-E5-001",
                    "langgraph",
                    "technical_smoke",
                ): _row()
            },
        ):
            payload = generate_dashboard.build_payload("retail")
        by_id = {framework["id"]: framework for framework in payload["frameworks"]}
        html = generate_dashboard.render_html(payload)

        self.assertEqual(by_id["langgraph"]["evidence_status"], "available")
        self.assertEqual(
            by_id["openai_agents_sdk"]["evidence_status"], "not_available"
        )
        self.assertEqual(by_id["crewai"]["evidence_status"], "not_available")
        self.assertIn("SYNTHETIC TECHNICAL VALIDATION", html)
        self.assertIn("NOT BENCHMARK SCORES", html)
        self.assertIn("no simulated ranking", html)
        self.assertNotIn("Pass rate", html)
        self.assertNotIn("Median latency", html)

    def test_prototype_transfer_calls_match_non_mutating_contract(self):
        prototype = (
            generate_dashboard.ROOT / "docs" / "WS3_dashboard_prototype.html"
        ).read_text(encoding="utf-8")
        calls = [
            fragment.split("}],", 1)[0]
            for fragment in prototype.split('"transfer_to_human_agents"')[1:]
        ]

        self.assertGreater(len(calls), 0)
        for call in calls:
            self.assertIn("args:{summary:", call)
            self.assertIn("mut:false", call)
            self.assertNotIn("order_id:", call)
            self.assertNotIn("reason:", call)


if __name__ == "__main__":
    unittest.main()
