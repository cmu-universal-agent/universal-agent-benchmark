import unittest
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

from adapter.tau_retail_env import (
    MAX_TAU_WORKER_NOISE_LINES,
    TAU_WORKER_RESPONSE_PREFIX,
    TauRetailEnv,
)


class TauRetailEnvTests(unittest.TestCase):
    def test_call_tool_serializes_the_shared_worker_transaction(self):
        env = TauRetailEnv.__new__(TauRetailEnv)
        env._tool_lock = threading.RLock()
        env._env = True
        env.allowed_tools = frozenset({"list_all_product_types"})
        env._trace = Mock()
        env._mutation_count = 0
        env._state = Mock(return_value={"agent_db_hash": "same"})
        counter_lock = threading.Lock()
        active = 0
        max_active = 0

        def request(_payload):
            nonlocal active, max_active
            with counter_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            with counter_lock:
                active -= 1
            return {"result": []}

        env._request = request
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: env.call_tool("list_all_product_types", {}),
                    range(2),
                )
            )

        self.assertTrue(all(result.ok for result in results))
        self.assertEqual(max_active, 1)

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
