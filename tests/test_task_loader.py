import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from adapter.task_loader import load_task, task_from_dict
from adapter.validation import AMBIGUOUS_EVALUATOR_ONLY_KEYS, STRICT_EVALUATOR_ONLY_KEYS


ROOT = Path(__file__).resolve().parents[1]
STRICT_EVALUATOR_ONLY_ALIASES = tuple(sorted(STRICT_EVALUATOR_ONLY_KEYS))
AMBIGUOUS_EVALUATOR_ONLY_ALIASES = tuple(sorted(AMBIGUOUS_EVALUATOR_ONLY_KEYS))


def _valid_v1_case() -> dict:
    fixtures = json.loads(
        (ROOT / "tests" / "fixtures" / "schema_cases.json").read_text(
            encoding="utf-8"
        )
    )
    return copy.deepcopy(
        next(
            fixture["document"]
            for fixture in fixtures["fixtures"]
            if fixture["name"] == "valid_benchmark_case"
        )
    )


class TaskLoaderSemanticValidationTests(unittest.TestCase):
    def _load_case(self, case: dict):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "task_case.json"
            path.write_text(json.dumps(case), encoding="utf-8")
            return load_task(path)

    def test_rejects_every_strict_evaluator_alias_through_load_task(self):
        for alias in STRICT_EVALUATOR_ONLY_ALIASES:
            case = _valid_v1_case()
            case["input"]["data"] = {
                "safe_input": {
                    "nested": {
                        alias: "evaluator-only value",
                    }
                }
            }

            with self.subTest(alias=alias):
                with self.assertRaisesRegex(
                    ValueError,
                    rf"forbidden key at <root>\.input\.data\.safe_input"
                    rf"\.nested\.{alias}",
                ):
                    self._load_case(case)

    def test_ambiguous_evaluator_alias_does_not_block_load_task(self):
        # These are common dictionary words (e.g. "note", "gold") that could
        # legitimately be a domain field name. They are still flagged by the
        # offline dataset reviewer (scripts/validate_core_pilot.py), but must
        # not hard-crash every framework's task load over a word collision.
        for alias in AMBIGUOUS_EVALUATOR_ONLY_ALIASES:
            case = _valid_v1_case()
            case["input"]["data"] = {
                "safe_input": {
                    "nested": {
                        alias: "ambiguous domain value",
                    }
                }
            }

            with self.subTest(alias=alias):
                task = self._load_case(case)
                self.assertIn("ambiguous domain value", task.prompt)

    def test_legitimate_domain_fields_render_through_load_task(self):
        case = _valid_v1_case()
        case["input"]["data"] = {
            "clinical_note": "Patient reports improving symptoms.",
            "expected_delivery_date": "2026-08-01",
            "order_snapshot": {
                "status": "in_transit",
                "customer_message": "Please confirm the delivery window.",
            },
        }

        task = self._load_case(case)

        self.assertIn("clinical_note", task.prompt)
        self.assertIn("Patient reports improving symptoms.", task.prompt)
        self.assertIn("expected_delivery_date", task.prompt)
        self.assertIn("customer_message", task.prompt)

    def test_rejects_evaluator_data_before_prompt_rendering(self):
        case = _valid_v1_case()
        case["input"]["data"]["gold_answer"] = "evaluator-only answer"

        with patch(
            "adapter.task_loader.render_v1_prompt",
            side_effect=AssertionError("prompt rendering must not run"),
        ):
            with self.assertRaisesRegex(
                ValueError,
                r"forbidden key at <root>\.input\.data\.gold_answer",
            ):
                task_from_dict(case)

    def test_valid_v1_case_still_renders(self):
        task = task_from_dict(_valid_v1_case())

        self.assertEqual(task.schema_version, "1.0")
        self.assertIn("Synthetic evidence", task.prompt)

    def test_legacy_task_compatibility_is_unchanged(self):
        task = task_from_dict(
            {
                "task_id": "SMOKE-001",
                "vertical": "smoke_test",
                "prompt": "Return JSON.",
            }
        )

        self.assertIsNone(task.schema_version)
        self.assertEqual(task.prompt, "Return JSON.")


if __name__ == "__main__":
    unittest.main()
