import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from adapter.e5_session import run_e5_session
from adapter.schemas import BenchmarkTask


class E5SessionTests(unittest.TestCase):
    def test_runs_agent_until_pinned_simulator_stops(self):
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
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_: next(responses))
            )
        )
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
                    "model": "openai/test",
                    "seed": 0,
                    "task_instructions": "Ask for help.",
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
                patch("adapter.e5_session.OpenAI", return_value=client),
            ):
                result = run_e5_session(
                    task,
                    lambda _: (
                        '{"resolution":"done"}',
                        {
                            "input_tokens": 7,
                            "output_tokens": 2,
                            "total_tokens": 9,
                        },
                    ),
                )

        self.assertEqual(result.final_output, '{"resolution":"done"}')
        self.assertEqual(result.token_usage["total_tokens"], 9)
        self.assertEqual(result.simulator["termination"], "###STOP###")
        self.assertEqual(len(result.assistant_turns), 2)


if __name__ == "__main__":
    unittest.main()
