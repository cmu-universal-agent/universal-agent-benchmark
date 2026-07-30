from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import serve_ws3_playground as playground


class Ws3PlaygroundTests(unittest.TestCase):
    def test_request_validation(self) -> None:
        self.assertEqual(
            playground._validated_request(
                {
                    "framework": "openai_agents_sdk",
                    "prompt": "  help with my order  ",
                }
            ),
            ("openai_agents_sdk", "help with my order"),
        )
        for data in (
            {},
            {"framework": "crewai", "prompt": "help"},
            {"framework": "langgraph", "prompt": ""},
            {"framework": "langgraph", "prompt": "x" * 4_001},
        ):
            with self.assertRaises(playground.RequestError):
                playground._validated_request(data)

    def test_live_result_is_allowlisted(self) -> None:
        fake_result = SimpleNamespace(
            success=True,
            final_output='{"resolution":"done"}',
            error=None,
            latency_seconds=1.234,
            token_usage={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            tool_calls=[
                {
                    "tool_name": "get_order_details",
                    "arguments": {"order_id": "PRIVATE-ORDER"},
                    "outcome": "success",
                    "result": {"private": "PRIVATE-RESULT"},
                    "state_before_sha256": "a" * 64,
                    "state_after_sha256": "b" * 64,
                }
            ],
        )
        fake_runner = SimpleNamespace(run_retail_task=lambda task, seed: fake_result)

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch.object(
                playground.importlib,
                "import_module",
                return_value=fake_runner,
            ),
        ):
            result = playground.run_live(
                "openai_agents_sdk",
                "help with my order",
            )

        self.assertEqual(result["trace"][0]["tool_name"], "get_order_details")
        self.assertTrue(result["trace"][0]["state_changed"])
        rendered = str(result)
        for forbidden in (
            "PRIVATE-ORDER",
            "PRIVATE-RESULT",
            "state_before_sha256",
            "state_after_sha256",
            "arguments",
            "result_sha256",
            "final_state",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_live_run_requires_local_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                playground.RequestError,
                "OPENAI_API_KEY",
            ):
                playground.run_live("langgraph", "help")


if __name__ == "__main__":
    unittest.main()
