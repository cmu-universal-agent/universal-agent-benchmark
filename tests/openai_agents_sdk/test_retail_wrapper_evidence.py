"""Offline proof that the OpenAI Agents SDK retail wrapper satisfies WS3 contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_ws3_tau_retail_contract.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.runtime import GenerationSettings, resolve_generation_settings
from adapter.task_loader import load_task
from frameworks.openai_agents_sdk import retail_run, run as openai_run
from frameworks.openai_agents_sdk.retail_evidence import build_wrapper_evidence


class TestOpenAIRetailWrapperEvidence(unittest.TestCase):
    def test_main_entrypoint_routes_retail_cases(self) -> None:
        task = load_task(
            ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json"
        )
        expected = object()

        with patch.object(
            retail_run,
            "run_retail_task",
            return_value=expected,
        ) as run_retail:
            result = openai_run.run_task(task)

        self.assertIs(result, expected)
        run_retail.assert_called_once_with(task)

    def test_openai_wrapper_evidence_passes_contract_validator(self) -> None:
        evidence = build_wrapper_evidence()
        self.assertEqual(evidence["framework"], "openai_agents_sdk")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "wrapper_evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--wrapper-evidence", str(evidence_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WS3_TAU_RETAIL_CONTRACT_OK", result.stdout)
        self.assertIn("wrapper_evidence=1", result.stdout)

    def test_explicit_zero_seed_is_preserved(self) -> None:
        task = load_task(
            ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json"
        )
        requested = GenerationSettings(
            temperature=0.0,
            max_output_tokens=256,
            seed=0,
        )
        resolution = resolve_generation_settings(requested, requested)

        with (
            patch.object(
                retail_run,
                "configured_generation_settings",
                return_value=GenerationSettings(0.0, 256, None),
            ),
            patch.object(
                retail_run,
                "_build_agent",
                return_value=(object(), resolution),
            ),
            patch.object(
                retail_run,
                "_run_retail_agent",
                return_value=(
                    '{"resolution":"done","actions_taken":[]}',
                    {
                        "input_tokens": 1,
                        "output_tokens": 1,
                        "total_tokens": 2,
                    },
                    [],
                    {"state_sha256": "synthetic"},
                ),
            ),
        ):
            result = retail_run.run_retail_task(task, seed=0)

        self.assertTrue(result.success)
        self.assertEqual(result.seed, 0)

    def test_model_construction_failure_is_recorded(self) -> None:
        task = load_task(
            ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json"
        )

        with (
            patch.object(
                retail_run,
                "_build_agent",
                side_effect=RuntimeError("synthetic model build failure"),
            ),
            patch.object(retail_run, "_run_retail_agent") as run_agent,
        ):
            result = retail_run.run_retail_task(task)

        self.assertFalse(result.success)
        self.assertTrue(result.raw_metadata["model_construction_failed"])
        run_agent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
