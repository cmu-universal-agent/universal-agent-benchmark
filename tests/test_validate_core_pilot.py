import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import prepare_core_pilot as prepare


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_core_pilot.py"
TASK_IDS = ("H1", "H2", "H4", "H5", "E1", "E2", "E3", "E5")


def _gold_payload(task_id: str) -> dict:
    return {
        "H1": {"result": {"decision": "yes"}},
        "H2": {"result": {"urgency": "routine"}},
        "H4": {
            "result": {
                "symptoms": ["fatigue"],
                "history": [],
                "risks": [],
                "next_steps": ["follow up"],
            }
        },
        "H5": {"result": {"boundary_action": "refuse"}},
        "E1": {"result": {"trend_direction": "stable"}},
        "E2": {
            "result": {
                "recommendations": [{"product_id": "P1", "rank": 1}],
                "constraints_satisfied": True,
            }
        },
        "E3": {
            "result": {"decision": "return_allowed"},
            "expected_actions": [{"name": "return_delivered_order_items"}],
        },
        "E5": {
            "expected_actions": [{"name": "return_delivered_order_items"}],
            "expected_communications": [{"name": "confirm_return"}],
            "state_validation": "tau simulator final-state comparison",
            "initial_state_hash": "initial",
            "final_state": {
                "expected_agent_db_hash": "expected",
                "expected_user_db_hash": None,
                "gold_replay_clean": True,
            },
        },
    }[task_id]


def _write_task(root: Path, task_id: str) -> tuple[dict, dict]:
    case_id = f"{task_id}-TEST-001"
    case = prepare._case(
        case_id=case_id,
        task_id=task_id,
        vertical="healthcare" if task_id.startswith("H") else "ecommerce",
        data={"request": f"Synthetic {task_id} review input."},
        dataset="synthetic-regression-fixture",
        source_id=f"source-{task_id}",
        source_split="fixture",
        split="pilot",
        difficulty="easy",
        tags=["regression_fixture"],
        allowed_tools=(
            ["lookup_order", "update_order"] if task_id == "E5" else []
        ),
    )
    gold = prepare._gold(case, _gold_payload(task_id), "source_derived")
    (root / "cases").mkdir(parents=True, exist_ok=True)
    (root / "gold").mkdir(parents=True, exist_ok=True)
    (root / "cases" / f"task_{task_id.lower()}_001.json").write_text(
        json.dumps(case),
        encoding="utf-8",
    )
    (root / "gold" / f"{task_id.lower()}.jsonl").write_text(
        json.dumps(gold) + "\n",
        encoding="utf-8",
    )
    return case, gold


def _write_artifact_indexes(
    root: Path,
    cases: list[dict],
    gold: list[dict],
    *,
    expected_per_task: int = 1,
) -> None:
    manifest = prepare._new_split_manifest(seed=42)
    report = prepare._new_coverage_report(expected_per_task, seed=42)
    report["status"] = "offline_evaluation_ready"
    for task_id in TASK_IDS:
        task_cases = [case for case in cases if case["task_id"] == task_id]
        task_gold = [row for row in gold if row["task_id"] == task_id]
        if not task_cases:
            continue
        manifest["tasks"][task_id] = prepare._split_manifest_entries(task_cases)
        report["tasks"][task_id] = {
            "status": "generated_for_review",
            "cases": len(task_cases),
            "gold_records": len(task_gold),
        }
    manifest["total_cases"] = len(cases)
    report["total_cases"] = len(cases)
    report["total_gold_records"] = len(gold)
    (root / "split_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (root / "coverage_report.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )


def _write_complete_output(root: Path) -> None:
    records = [_write_task(root, task_id) for task_id in TASK_IDS]
    _write_artifact_indexes(
        root,
        [case for case, _ in records],
        [gold for _, gold in records],
    )


def _validate(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--input",
            str(path),
            "--expected-per-task",
            "1",
            "--expected-e5",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@unittest.skipUnless(
    importlib.util.find_spec("jsonschema") is not None,
    "jsonschema is not installed in this virtual environment",
)
class CorePilotCompletenessTests(unittest.TestCase):
    def test_rejects_missing_output_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = _validate(Path(temporary) / "not-generated")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing cases directory", result.stdout + result.stderr)
        self.assertIn("missing gold directory", result.stdout + result.stderr)

    def test_rejects_partial_output_missing_one_task(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            records = [_write_task(output, task_id) for task_id in TASK_IDS[:-1]]
            _write_artifact_indexes(
                output,
                [case for case, _ in records],
                [gold for _, gold in records],
            )

            result = _validate(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing task IDs: ['E5']", result.stdout + result.stderr)
        self.assertIn("E5: expected 1 cases, found 0", result.stdout + result.stderr)

    def test_accepts_complete_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            _write_complete_output(output)

            result = _validate(output)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cases=8 gold=8 leakage=0", result.stdout)

    def test_rejects_missing_required_artifacts(self):
        for artifact in ("split_manifest.json", "coverage_report.json"):
            with self.subTest(artifact=artifact):
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary)
                    _write_complete_output(output)
                    (output / artifact).unlink()

                    result = _validate(output)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"missing required artifact: {artifact}", result.stdout)

    def test_rejects_empty_evaluator_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            _write_complete_output(output)
            gold_path = output / "gold" / "h1.jsonl"
            row = json.loads(gold_path.read_text(encoding="utf-8"))
            row["gold"] = {}
            gold_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

            result = _validate(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gold payload must not be empty", result.stdout)

    def test_rejects_manifest_case_id_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            _write_complete_output(output)
            manifest_path = output / "split_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["tasks"]["H1"][0]["case_id"] = "H1-WRONG-001"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = _validate(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest case IDs do not match generated cases", result.stdout)

    def test_reports_non_object_case_json_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            _write_complete_output(output)
            case_path = output / "cases" / "task_h1_001.json"
            case_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

            result = _validate(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(
            "task_h1_001.json: expected a JSON object, found list",
            result.stdout + result.stderr,
        )

    def test_reports_non_object_gold_json_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            _write_complete_output(output)
            gold_path = output / "gold" / "h1.jsonl"
            gold_path.write_text(json.dumps([1, 2, 3]) + "\n", encoding="utf-8")

            result = _validate(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(
            "h1.jsonl:1: expected a JSON object, found list",
            result.stdout + result.stderr,
        )

    def test_rejects_incorrect_report_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            _write_complete_output(output)
            report_path = output / "coverage_report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["tasks"]["H1"]["cases"] = 2
            report["total_cases"] = 9
            report_path.write_text(json.dumps(report), encoding="utf-8")

            result = _validate(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("coverage H1 case count mismatch", result.stdout)
        self.assertIn("coverage total_cases mismatch", result.stdout)


if __name__ == "__main__":
    unittest.main()
