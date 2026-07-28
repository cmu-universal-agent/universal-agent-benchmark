import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import demo_ws3_offline as demo
from scripts import validate_ws3_tau_retail_contract as validator


class Ws3TauRetailContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = validator._load(validator.CONTRACT_PATH)
        cls.fixture = validator._load(validator.FIXTURE_PATH)
        cls.operations = validator._validate_registry(cls.contract, cls.fixture)

    def validate(self, fixture):
        return validator._validate_scenarios(
            self.contract, fixture, self.operations
        )

    def test_valid_fixture_passes(self):
        self.assertEqual(self.validate(copy.deepcopy(self.fixture)), (7, 8))

    def test_arguments_valid_is_derived_from_schema(self):
        fixture = copy.deepcopy(self.fixture)
        call = fixture["scenarios"][1]["events"][0]["call"]
        call["arguments"] = {}
        with self.assertRaisesRegex(AssertionError, "argument-validity mismatch"):
            self.validate(fixture)

    def test_was_allowed_is_derived_from_scenario(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["scenarios"][1]["allowed_tools"] = []
        with self.assertRaisesRegex(AssertionError, "allowed-tools mismatch"):
            self.validate(fixture)

    def test_scenario_must_start_from_clean_reset(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["scenarios"][0]["initial_state"]["sequence_index"] = 1
        with self.assertRaisesRegex(AssertionError, "initial sequence is not zero"):
            self.validate(fixture)

    def test_calls_cannot_mix_run_ids(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["scenarios"][-1]["events"][1]["call"]["run_id"] = "run-other-001"
        with self.assertRaisesRegex(AssertionError, "mixed run ids"):
            self.validate(fixture)

    def test_contract_demo_writes_sanitized_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence.json"
            html_output = Path(temporary) / "demo.html"
            summary = demo.run_demo(output)
            demo.write_html(summary, html_output)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            html = html_output.read_text(encoding="utf-8")

        self.assertEqual(summary["tools"], 16)
        self.assertEqual(summary["duplicate_error"], "duplicate_action")
        self.assertFalse(summary["duplicate_state_changed"])
        self.assertEqual(evidence["wrapper_version"], "synthetic-contract-fixture")
        self.assertIn("NOT BENCHMARK SCORES", html)
        self.assertNotIn("evaluator_only", html)


if __name__ == "__main__":
    unittest.main()
