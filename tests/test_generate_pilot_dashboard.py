from __future__ import annotations

import unittest

from scripts import generate_pilot_dashboard as pilot_dashboard


class GeneratePilotDashboardTests(unittest.TestCase):
    def test_frozen_run_matrix_totals(self) -> None:
        payload = pilot_dashboard.build_payload()

        self.assertEqual(payload["gate_status"], "technical_smoke_only")
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
        html = pilot_dashboard.render_html(pilot_dashboard.build_payload())

        self.assertIn("technical_smoke_only", html)
        self.assertEqual(html.count(">pending<"), 8 * 3)
        self.assertNotIn("correct", html)
        self.assertNotIn("incorrect", html)


if __name__ == "__main__":
    unittest.main()
