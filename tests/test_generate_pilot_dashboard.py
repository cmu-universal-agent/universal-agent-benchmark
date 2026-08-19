from __future__ import annotations

import unittest

from scripts import generate_pilot_dashboard as pilot_dashboard


class GeneratePilotDashboardTests(unittest.TestCase):
    def _aggregate(self) -> tuple[dict, dict]:
        rows = []
        for task in pilot_dashboard.WS4_TASKS:
            for framework in pilot_dashboard.KNOWN_FRAMEWORK_ORDER:
                is_e5 = task["task_id"] == "E5"
                rows.append({
                    "task_id": task["task_id"], "framework": framework,
                    "n": 6 if is_e5 else 10, "process_success": 6 if is_e5 else 10,
                    "schema_valid": 6 if is_e5 else 10, "scored_n": 0 if is_e5 else 10,
                    "content_pass": 0 if is_e5 else 5, "mean_score": None if is_e5 else 0.5,
                    "e5_pass": 0, "e5_fail": 6 if is_e5 else 0, "e5_error": 0,
                    "e5_sweep_valid": True if is_e5 else None, "h5_pending": 0,
                    "avg_latency_seconds": 1.0, "input_tokens": 1, "output_tokens": 1,
                    "estimated_cost_usd": 0.001,
                })
        repeats = [
            {"case_id": task["representative_case_id"], "task_id": task["task_id"],
             "framework": framework, "observations": [1, 1, 1], "complete": True, "stable": True}
            for task in pilot_dashboard.WS4_TASKS
            for framework in pilot_dashboard.KNOWN_FRAMEWORK_ORDER
        ]
        aggregate = {
            "schema_version": "1.0", "generated_at": "now", "experiment_id": "exp",
            "status": "candidate_claims_approved_public_release_pending",
            "claim_boundary": "No overall winner.", "invalid_e5_frameworks": [],
            "rows": rows, "targeted_repeats": repeats,
        }
        freeze = {
            "experiment_id": "exp", "status": "formal_scoring_complete_privacy_confirmed",
            "owner_confirmations": {"privacy_boundary_confirmed": True},
            "privacy": {"aggregate_forbidden_field_matches": 0, "public_release_authorized": False},
        }
        return aggregate, freeze

    def test_frozen_run_matrix_totals(self) -> None:
        payload = pilot_dashboard.build_payload()

        report = pilot_dashboard.REPORT_PATH.read_text(encoding="utf-8")
        self.assertIn(f"- Gate status: `{payload['gate_status']}`", report)
        self.assertEqual(len(payload["tasks"]), 8)
        self.assertEqual(payload["totals"]["cases"], 60)
        self.assertEqual(payload["totals"]["preflights"], 24)
        self.assertEqual(payload["totals"]["main_runs"], 180)
        self.assertEqual(payload["totals"]["repeats"], 48)
        self.assertEqual(payload["totals"]["controlled_total"], 228)

    def test_e5_task_uses_four_cases(self) -> None:
        payload = pilot_dashboard.build_payload()
        e5 = next(t for t in payload["tasks"] if t["task_id"] == "E5")

        self.assertEqual(e5["cases"], 4)
        self.assertEqual(e5["representative_case_id"], "E5-001")
        self.assertEqual(e5["main_runs"], 12)
        self.assertEqual(e5["repeats"], 6)
        self.assertEqual(e5["controlled_total"], 18)

    def test_render_html_has_no_fabricated_status(self) -> None:
        payload = pilot_dashboard.build_payload()
        html = pilot_dashboard.render_html(payload)

        self.assertIn(payload["gate_status"], html)
        self.assertNotIn("No controlled-pilot run has executed", html)
        self.assertEqual(html.count(">pending<"), 8 * 3)
        self.assertNotIn("correct", html)
        self.assertNotIn("incorrect", html)

    def test_privacy_confirmed_aggregate_renders_candidate_results(self) -> None:
        aggregate, freeze = self._aggregate()
        html = pilot_dashboard.render_html(pilot_dashboard.build_payload(aggregate, freeze))

        self.assertIn("Privacy-reviewed aggregate candidate", html)
        self.assertIn("Claims approved", html)
        self.assertIn("public release is not authorized", html)
        self.assertIn("Targeted-repeat stability: 24/24", html)
        self.assertNotIn("experiment_id", html)

    def test_aggregate_rejects_private_fields(self) -> None:
        aggregate, freeze = self._aggregate()
        aggregate["rows"][0]["run_id"] = "private"

        with self.assertRaisesRegex(ValueError, "public allowlist"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_duplicate_task_framework_rows(self) -> None:
        aggregate, freeze = self._aggregate()
        aggregate["rows"][1] = aggregate["rows"][0].copy()

        with self.assertRaisesRegex(ValueError, "incomplete or duplicated"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_non_boolean_release_flag(self) -> None:
        aggregate, freeze = self._aggregate()
        freeze["privacy"]["public_release_authorized"] = "false"

        with self.assertRaisesRegex(ValueError, "must be boolean"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_non_numeric_metric(self) -> None:
        aggregate, freeze = self._aggregate()
        aggregate["rows"][0]["schema_valid"] = "<private>"

        with self.assertRaisesRegex(ValueError, "invalid types"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_shifted_per_pair_counts(self) -> None:
        aggregate, freeze = self._aggregate()
        aggregate["rows"][0]["n"] = 9
        aggregate["rows"][1]["n"] = 11

        with self.assertRaisesRegex(ValueError, "frozen n=10"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_wrong_representative_case(self) -> None:
        aggregate, freeze = self._aggregate()
        aggregate["targeted_repeats"][0]["case_id"] = "WRONG"

        with self.assertRaisesRegex(ValueError, "frozen representative ID"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_incomplete_observation_set(self) -> None:
        aggregate, freeze = self._aggregate()
        aggregate["targeted_repeats"][0]["observations"] = []

        with self.assertRaisesRegex(ValueError, "three observations"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_pending_h5_scoring(self) -> None:
        aggregate, freeze = self._aggregate()
        h5 = next(row for row in aggregate["rows"] if row["task_id"] == "H5")
        h5["h5_pending"] = 1

        with self.assertRaisesRegex(ValueError, "h5_pending=0"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_inconsistent_e5_sweep_list(self) -> None:
        aggregate, freeze = self._aggregate()
        aggregate["invalid_e5_frameworks"] = ["openai_agents_sdk"]

        with self.assertRaisesRegex(ValueError, "contradicts E5 row validity"):
            pilot_dashboard.build_payload(aggregate, freeze)

    def test_aggregate_rejects_invalid_numeric_relationships(self) -> None:
        mutations = (
            ("process_success", 11, "process and schema counts"),
            ("content_pass", 11, "content pass and scored counts"),
            ("mean_score", 1.1, "between 0 and 1"),
            ("estimated_cost_usd", -0.01, "finite and non-negative"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                aggregate, freeze = self._aggregate()
                aggregate["rows"][0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    pilot_dashboard.build_payload(aggregate, freeze)


if __name__ == "__main__":
    unittest.main()
