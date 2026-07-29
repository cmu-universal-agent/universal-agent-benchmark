import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prepare_core_pilot", ROOT / "scripts" / "prepare_core_pilot.py"
)
PREPARE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PREPARE)

REPLAY_SPEC = importlib.util.spec_from_file_location(
    "fill_e5_replay", ROOT / "scripts" / "fill_e5_replay.py"
)
REPLAY = importlib.util.module_from_spec(REPLAY_SPEC)
assert REPLAY_SPEC.loader is not None
REPLAY_SPEC.loader.exec_module(REPLAY)


class FakeReplayEnv:
    def __init__(self, fail: bool = False):
        self.actions = []
        self.fail = fail

    def make_tool_call(self, tool_name, requestor, **arguments):
        if self.fail:
            raise ValueError("synthetic failure")
        self.actions.append((tool_name, requestor, arguments))

    def get_db_hash(self):
        return f"agent-{len(self.actions)}"

    def get_user_db_hash(self):
        return None


class E5ConversionTests(unittest.TestCase):
    def test_owner_batch_converts_without_publishing_gold(self):
        row = {
            "case_id": "E5-SYNTH-001",
            "source": {
                "benchmark": "synthetic-retail",
                "split": "review",
                "task_ref": "synthetic-1",
            },
            "user_simulator": {"task_instructions": "Resolve the synthetic order."},
            "initial_state_ref": "snapshot-synthetic",
            "initial_state_hash": "a" * 64,
            "allowed_tools": {
                "read": ["get_order_details"],
                "write": ["cancel_pending_order"],
                "generic": ["transfer_to_human_agents"],
            },
            "gold_write_actions": [
                {
                    "action_id": "write-1",
                    "tool": "cancel_pending_order",
                    "arguments": {"order_id": "ORDER-SYNTH", "reason": "requested"},
                }
            ],
            "required_actions": [
                {
                    "id": "required-1",
                    "kind": "write",
                    "tool": "cancel_pending_order",
                    "gold_action_ref": "write-1",
                }
            ],
            "final_state": {"comparison": "hash", "gold_replay_clean": True},
            "response_contract": {
                "required_info": [
                    {
                        "id": "status",
                        "match_type": "substring",
                        "values": ["cancelled"],
                    }
                ]
            },
            "evaluation": {"primary": "criterion_a_and_b"},
        }
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            batch_path = Path(temp_dir) / "E5_cases_batch1.json"
            batch_path.write_text(json.dumps({"cases": [row]}), encoding="utf-8")
            with patch.object(PREPARE, "E5_LOCAL_OWNER_BATCH", batch_path):
                cases, gold, stats = PREPARE.convert_e5(1, 42)

        self.assertEqual(cases[0]["case_id"], "E5-SYNTH-001")
        self.assertEqual(
            cases[0]["input"]["data"],
            {"customer_scenario_ref": "synthetic-1"},
        )
        self.assertNotIn("task_instructions", json.dumps(cases[0]))
        self.assertEqual(
            cases[0]["allowed_tools"],
            [
                "cancel_pending_order",
                "get_order_details",
                "transfer_to_human_agents",
            ],
        )
        self.assertNotIn("gold_write_actions", json.dumps(cases[0]))
        self.assertEqual(gold[0]["review"]["status"], "approved")
        self.assertEqual(
            gold[0]["gold"]["expected_actions"][0]["gold_action_ref"],
            "write-1",
        )
        self.assertEqual(stats["retail_tool_registry_size"], 3)

    def test_replay_fill_preserves_input_and_hard_fails(self):
        action = {
            "action_id": "1_0",
            "tool": "cancel_pending_order",
            "arguments": {"order_id": "ORDER-SYNTH"},
        }
        document = {
            "pending_fill": "source.version, initial_state_hash, user_simulator.model",
            "cases": [
                {
                    "case_id": "E5-001",
                    "source": {"task_ref": "1", "version": "<pin>"},
                    "initial_state_ref": "<snapshot>",
                    "initial_state_hash": None,
                    "gold_write_actions": [action],
                    "final_state": {
                        "expect_unchanged": False,
                        "gold_replay_clean": False,
                    },
                }
            ],
        }
        tasks = {
            "1": {
                "evaluation_criteria": {
                    "actions": [
                        {
                            "action_id": "1_0",
                            "name": action["tool"],
                            "arguments": action["arguments"],
                        }
                    ]
                }
            }
        }

        filled = REPLAY.fill_replay_fields(
            document,
            FakeReplayEnv,
            tasks,
            "pinned-commit",
            "data/retail/db.json",
        )

        self.assertEqual(filled["cases"][0]["initial_state_hash"], "agent-0")
        self.assertEqual(
            filled["cases"][0]["final_state"]["expected_agent_db_hash"],
            "agent-1",
        )
        self.assertTrue(filled["cases"][0]["final_state"]["gold_replay_clean"])
        self.assertEqual(filled["pending_fill"], "user_simulator.model")
        self.assertIsNone(document["cases"][0]["initial_state_hash"])
        with self.assertRaises(REPLAY.ReplayError):
            REPLAY.fill_replay_fields(
                document,
                lambda: FakeReplayEnv(fail=True),
                tasks,
                "pinned-commit",
                "data/retail/db.json",
            )


if __name__ == "__main__":
    unittest.main()
