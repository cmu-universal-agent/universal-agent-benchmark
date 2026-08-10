import unittest
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

from adapter.tau_retail_env import (
    MAX_TAU_WORKER_NOISE_LINES,
    TAU_WORKER_RESPONSE_PREFIX,
    TauRetailEnv,
)


class TauRetailEnvTests(unittest.TestCase):
    def test_request_ignores_worker_stdout_noise(self):
        env = TauRetailEnv.__new__(TauRetailEnv)
        env._worker = SimpleNamespace(
            stdin=StringIO(),
            stdout=StringIO(
                "tau import log\n"
                + TAU_WORKER_RESPONSE_PREFIX
                + '{"ok": true, "value": 1}\n'
            ),
            stderr=StringIO(),
        )

        self.assertEqual(env._request({"op": "state"})["value"], 1)

    def test_request_rejects_unbounded_worker_stdout_noise(self):
        env = TauRetailEnv.__new__(TauRetailEnv)
        env._worker = SimpleNamespace(
            stdin=StringIO(),
            stdout=StringIO("noise\n" * (MAX_TAU_WORKER_NOISE_LINES + 1)),
            stderr=StringIO(),
        )

        with self.assertRaisesRegex(RuntimeError, "stdout-noise limit"):
            env._request({"op": "state"})

    def test_failed_reset_does_not_mark_environment_ready(self):
        env = TauRetailEnv.__new__(TauRetailEnv)
        env.seed = 0
        env.case_id = None
        env.reset_id = None
        env._env = None
        env._request = Mock(side_effect=RuntimeError("source error"))

        with self.assertRaisesRegex(RuntimeError, "source error"):
            env.reset("E5-001", "reset-1")

        self.assertIsNone(env.case_id)
        self.assertIsNone(env.reset_id)
        self.assertIsNone(env._env)


if __name__ == "__main__":
    unittest.main()
