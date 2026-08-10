import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from adapter.e5_session import E5_AGENT_SYSTEM_PROMPT, run_e5_session
from adapter.schemas import BenchmarkTask


class E5SessionTests(unittest.TestCase):
    def test_rejects_placeholder_instructions_before_provider_call(self):
        task = BenchmarkTask(
            task_id="E5",
            case_id="E5-001",
            vertical="retail",
            prompt="",
        )
        gold = {
            "case_id": task.case_id,
            "gold": {
                "user_simulator": {
                    "model": "<fixed-model>",
                    "seed": 0,
                    "task_instructions": ".",
                    "max_turns": 4,
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "E5.jsonl"
            path.write_text(json.dumps(gold) + "\n", encoding="utf-8")
            with (
                patch.dict(
                    os.environ,
                    {"BENCHMARK_E5_GOLD_PATH": str(path)},
                    clear=False,
                ),
                patch("adapter.e5_session.OpenAI") as client,
                self.assertRaisesRegex(RuntimeError, "non-placeholder"),
            ):
                run_e5_session(task, lambda _: ("", {}))
        client.assert_not_called()

    def test_runs_agent_until_pinned_simulator_stops(self):
        api_requests = []
        responses = iter(
            [
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="I need help.")
                        )
                    ],
                    usage=SimpleNamespace(
                        prompt_tokens=2,
                        completion_tokens=3,
                        total_tokens=5,
                    ),
                ),
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="###STOP###")
                        )
                    ],
                    usage=SimpleNamespace(
                        prompt_tokens=4,
                        completion_tokens=1,
                        total_tokens=5,
                    ),
                ),
            ]
        )
        def create(**kwargs):
            api_requests.append(kwargs)
            return next(responses)

        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)
            )
        )
        task = BenchmarkTask(
            task_id="E5",
            case_id="E5-001",
            vertical="retail",
            prompt="AGENT_VISIBLE_TASK_PROMPT",
        )
        gold = {
            "case_id": task.case_id,
            "gold": {
                "user_simulator": {
                    "model": "<fixed-model>",
                    "seed": 0,
                    "task_instructions": (
                        "Domain: retail\nReason for call:\n\tResolve an order.\n"
                        "Known info:\n\tA synthetic order id.\n"
                        "Unknown info:\n\tThe order status.\n"
                        "Task instructions:\n\tAsk for help."
                    ),
                    "max_turns": 4,
                },
                "response_contract": "DO_NOT_SEND_RESPONSE_CONTRACT",
                "gold_write_actions": ["DO_NOT_SEND_GOLD_ACTION"],
                "rubric": ["DO_NOT_SEND_RUBRIC"],
                "expected_state": "DO_NOT_SEND_EXPECTED_STATE",
                "expected_hash": "DO_NOT_SEND_HASH",
            },
        }

        agent_prompts = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "E5.jsonl"
            path.write_text(json.dumps(gold) + "\n", encoding="utf-8")
            with (
                patch.dict(
                    os.environ,
                    {"BENCHMARK_E5_GOLD_PATH": str(path)},
                    clear=False,
                ),
                patch("adapter.e5_session.OpenAI", return_value=client),
            ):
                result = run_e5_session(
                    task,
                    lambda prompt: (
                        agent_prompts.append(prompt) or '{"resolution":"done"}',
                        {"input_tokens": 7, "output_tokens": 2, "total_tokens": 9},
                    ),
                )

        self.assertEqual(result.final_output, '{"resolution":"done"}')
        self.assertEqual(result.token_usage["total_tokens"], 9)
        self.assertEqual(result.simulator["protocol_version"], "1.4")
        self.assertEqual(result.simulator["model"], "gpt-4o-mini")
        self.assertEqual(result.simulator["termination"], "###STOP###")
        self.assertEqual(len(result.assistant_turns), 2)
        outbound = json.dumps(api_requests)
        self.assertTrue(all(row["model"] == "gpt-4o-mini" for row in api_requests))
        self.assertNotIn("<fixed-model>", outbound)
        self.assertIn("Ask for help.", outbound)
        self.assertIn("Reason for call", outbound)
        self.assertIn("Known info", outbound)
        self.assertIn("Unknown info", outbound)
        self.assertNotIn("DO_NOT_SEND", outbound)
        self.assertNotIn("AGENT_VISIBLE_TASK_PROMPT", outbound)
        self.assertIn("AGENT_VISIBLE_TASK_PROMPT", agent_prompts[0])
        self.assertNotIn("actions_taken", E5_AGENT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
