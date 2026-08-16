#!/usr/bin/env python3
"""JSON-lines worker for the pinned private tau2 retail environment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.fill_e5_replay import load_tau_environment, verify_source
from adapter.tau_retail_env import TAU_WORKER_RESPONSE_PREFIX


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tau-root", required=True)
    parser.add_argument("--source-version", required=True)
    args = parser.parse_args()

    tau_root = Path(args.tau_root).resolve()
    verify_source(tau_root, args.source_version)
    factory = load_tau_environment(tau_root)
    environment = None

    for line in sys.stdin:
        try:
            request = json.loads(line)
            operation = request["op"]
            if operation == "reset":
                environment = factory()
                response = {"ok": True}
            elif environment is None:
                raise RuntimeError("reset must run before other operations")
            elif operation == "call":
                result = environment.make_tool_call(
                    request["tool"],
                    requestor="assistant",
                    **request["arguments"],
                )
                response = {"ok": True, "result": _jsonable(result)}
            elif operation == "state":
                response = {
                    "ok": True,
                    "agent_db_hash": environment.get_db_hash(),
                    "user_db_hash": environment.get_user_db_hash(),
                }
            else:
                raise ValueError(f"unknown operation: {operation}")
        except Exception as exc:
            response = {
                "ok": False,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        print(TAU_WORKER_RESPONSE_PREFIX + json.dumps(response, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
