"""Offline proof that the CrewAI retail wrapper satisfies the WS3 contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_ws3_tau_retail_contract.py"

os.environ.setdefault("CREWAI_STORAGE_DIR", str(ROOT / ".crewai"))
if sys.platform == "win32":
    os.environ.setdefault("LOCALAPPDATA", str(ROOT / ".crewai" / "test-appdata"))
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.runtime import GenerationSettings, resolve_generation_settings
from adapter.task_loader import load_task
from frameworks.crewai_agent import retail_run, run as crewai_run
from frameworks.crewai_agent.retail_evidence import build_wrapper_evidence


class TestCrewAIRetailWrapperEvidence(unittest.TestCase):
    def test_retail_agent_uses_the_bounded_iteration_limit(self) -> None:
        env = Mock()
        env.get_trace.return_value = []
        env.get_final_state.return_value = {}

        with (
            patch.object(retail_run, "make_retail_tools", return_value=[]),
            patch.object(crewai_run, "Agent") as agent_class,
            patch.object(crewai_run, "Task"),
            patch.object(crewai_run, "Crew") as crew_class,
            patch.object(
                crewai_run,
                "_extract_token_usage",
                return_value=({}, {}),
            ),
        ):
            crew_class.return_value.kickoff.return_value = "{}"
            retail_run._run_retail_agent(object(), env, "prompt", [])

        self.assertEqual(
            agent_class.call_args.kwargs["max_iter"],
            retail_run.MAX_RETAIL_ITERATIONS,
        )
        self.assertIs(
            agent_class.call_args.kwargs["step_callback"],
            retail_run._log_step,
        )

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
            result = crewai_run.run_task(task)

        self.assertIs(result, expected)
        run_retail.assert_called_once_with(task)

    def test_crewai_wrapper_evidence_passes_contract_validator(self) -> None:
        evidence = build_wrapper_evidence()
        self.assertEqual(evidence["framework"], "crewai")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "wrapper_evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--wrapper-evidence",
                    str(evidence_path),
                ],
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
                crewai_run,
                "_build_llm",
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
                    {"available": True, "crew_fields": {}},
                    [],
                    {"state_sha256": "synthetic"},
                ),
            ),
        ):
            result = retail_run.run_retail_task(task, seed=0)

        self.assertTrue(result.success)
        self.assertEqual(result.seed, 0)

    def test_run_attaches_shared_trace_state_and_usage(self) -> None:
        task = load_task(
            ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json"
        )
        requested = GenerationSettings(
            temperature=0.0,
            max_output_tokens=256,
            seed=42,
        )
        resolution = resolve_generation_settings(requested, requested)

        def run_boundary(_llm, env, _prompt, _allowed_tools):
            env.call_tool("get_order_details", {"order_id": "O5001"})
            return (
                '{"resolution":"reviewed","actions_taken":["get_order_details"]}',
                {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
                {"available": True, "crew_fields": {"successful_requests": 1}},
                env.get_trace(),
                env.get_final_state(),
            )

        with (
            patch.object(
                crewai_run,
                "_build_llm",
                return_value=(object(), resolution),
            ),
            patch.object(
                retail_run,
                "_run_retail_agent",
                side_effect=run_boundary,
            ),
        ):
            result = retail_run.run_retail_task(task)

        self.assertTrue(result.success)
        self.assertEqual(result.tool_call_count, 1)
        self.assertEqual(result.tool_calls[0]["tool_name"], "get_order_details")
        self.assertEqual(result.token_usage["total_tokens"], 5)
        self.assertIn("final_state", result.raw_metadata)
        self.assertTrue(result.raw_metadata["crewai_token_usage"]["available"])

    def test_model_construction_failure_is_recorded(self) -> None:
        task = load_task(
            ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json"
        )

        with (
            patch.object(
                crewai_run,
                "_build_llm",
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
