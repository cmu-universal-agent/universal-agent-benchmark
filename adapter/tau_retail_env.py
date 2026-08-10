"""Private formal-E5 bridge to the pinned tau2 retail environment."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adapter.retail_core.schemas import ToolResult
from adapter.retail_core.trace import Trace
from adapter.schemas import BenchmarkTask
from adapter.validation import validate_tool_arguments

ROOT = Path(__file__).resolve().parents[1]
TAU_WORKER_RESPONSE_PREFIX = "__TAU_WORKER_RESPONSE__="


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TauRetailEnv:
    """Expose pinned tau2 tools through the same interface as ``RetailEnv``."""

    def __init__(
        self,
        tau_root: Path,
        source_version: str,
        allowed_tools: list[str],
        seed: int,
        python_bin: Path,
    ) -> None:
        self.allowed_tools = frozenset(allowed_tools)
        self.seed = seed
        self.case_id: str | None = None
        self.reset_id: str | None = None
        self._env: Any = None
        self._trace = Trace(run_id=f"run-{uuid.uuid4().hex}")
        self._mutation_count = 0
        self._worker = subprocess.Popen(
            [
                str(python_bin),
                str(ROOT / "scripts" / "tau_retail_worker.py"),
                "--tau-root",
                str(tau_root),
                "--source-version",
                source_version,
            ],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._worker.stdin is None or self._worker.stdout is None:
            raise RuntimeError("tau2 worker pipes are unavailable")
        self._worker.stdin.write(json.dumps(payload) + "\n")
        self._worker.stdin.flush()
        while True:
            line = self._worker.stdout.readline()
            if not line:
                detail = (
                    self._worker.stderr.read().strip()
                    if self._worker.stderr is not None
                    else ""
                )
                raise RuntimeError(f"tau2 worker stopped unexpectedly: {detail}")
            if line.startswith(TAU_WORKER_RESPONSE_PREFIX):
                response = json.loads(line.removeprefix(TAU_WORKER_RESPONSE_PREFIX))
                break
        if not response.get("ok"):
            raise RuntimeError(
                f"{response.get('error_type')}: {response.get('message')}"
            )
        return response

    def _state(self) -> dict[str, Any]:
        return self._request({"op": "state"})

    def reset(self, case_id: str, reset_id: str, seed: int | None = None) -> dict[str, Any]:
        if seed is not None:
            self.seed = seed
        self._request({"op": "reset"})
        self.case_id = case_id
        self.reset_id = reset_id
        self._env = True
        self._trace = Trace(run_id=f"run-{uuid.uuid4().hex}")
        self._mutation_count = 0
        return {"case": {"case_id": case_id}, "state": self.get_final_state()}

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        retry_of: str | None = None,
    ) -> ToolResult:
        if self._env is None:
            raise RuntimeError("reset(case_id, reset_id, seed) must be called first")

        started_at = _utc_now()
        started = time.perf_counter()
        before = self._state()["agent_db_hash"]
        was_allowed = name in self.allowed_tools
        argument_errors = validate_tool_arguments(name, arguments)
        arguments_valid = not argument_errors
        error: dict[str, Any] | None = None
        data: Any = None

        if not was_allowed:
            error_type = "disallowed_tool"
            error_message = f"tool not in allowed_tools for this case: {name}"
        elif not arguments_valid:
            error_type = "invalid_arguments"
            error_message = "; ".join(argument_errors)
        else:
            try:
                data = self._request(
                    {"op": "call", "tool": name, "arguments": arguments}
                ).get("result")
                error_type = error_message = None
            except Exception as exc:
                error_type = "tool_runtime_failure"
                error_message = str(exc)

        after = self._state()["agent_db_hash"]
        state_changed = before != after
        if state_changed:
            self._mutation_count += 1
        ok = error_type is None
        if not ok:
            error = {
                "error_type": error_type,
                "message": error_message,
                "retryable": error_type == "tool_runtime_failure",
            }
        self._trace.record(
            tool_name=name,
            arguments=arguments,
            was_allowed=was_allowed,
            arguments_valid=arguments_valid,
            started_at=started_at,
            completed_at=_utc_now(),
            latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
            outcome="success" if ok else "rejected",
            result=data,
            error=error,
            state_before_sha256=before,
            state_after_sha256=after,
            retry_of=retry_of,
        )
        return ToolResult(
            ok=ok,
            data=data if isinstance(data, dict) else {"value": data} if ok else None,
            error_type=error_type,
            error_message=error_message,
            state_changed=state_changed,
        )

    def get_trace(self) -> list[dict[str, Any]]:
        return self._trace.to_tool_calls()

    def get_final_state(self) -> dict[str, Any]:
        if self._env is None:
            raise RuntimeError("environment has not been reset")
        state = self._state()
        return {
            "case_id": self.case_id,
            "reset_id": self.reset_id,
            "sequence_index": len(self._trace),
            "agent_db_hash": state["agent_db_hash"],
            "user_db_hash": state["user_db_hash"],
            "mutation_count": self._mutation_count,
        }

    def close(self) -> None:
        if self._worker.poll() is None:
            self._worker.terminate()
            self._worker.wait(timeout=5)


def make_retail_env(task: BenchmarkTask, *, data_dir: str, seed: int) -> Any:
    if task.task_id != "E5":
        from adapter.retail_core.env import RetailEnv

        return RetailEnv(data_dir=data_dir, seed=seed)

    tau_root = os.getenv("BENCHMARK_E5_TAU_ROOT")
    source_version = os.getenv("BENCHMARK_E5_SOURCE_VERSION")
    python_bin = os.getenv("BENCHMARK_E5_PYTHON")
    if not tau_root or not source_version or not python_bin:
        raise RuntimeError(
            "formal E5 requires BENCHMARK_E5_TAU_ROOT, "
            "BENCHMARK_E5_SOURCE_VERSION, and BENCHMARK_E5_PYTHON"
        )
    return TauRetailEnv(
        Path(tau_root),
        source_version,
        task.allowed_tools or [],
        seed,
        Path(python_bin),
    )


class TauReplayEnv:
    """``adapter.e5_evaluator.Env`` backed by the pinned tau2 worker."""

    def __init__(self, gold: dict[str, Any]) -> None:
        allowed = [
            tool
            for bucket in ("read", "write", "generic")
            for tool in gold["allowed_tools"][bucket]
        ]
        task = BenchmarkTask(
            task_id="E5",
            case_id=gold["case_id"],
            vertical="retail",
            prompt="",
            allowed_tools=allowed,
        )
        self._env = make_retail_env(task, data_dir="", seed=0)
        self._env.reset(gold["case_id"], f"evaluation-{uuid.uuid4().hex}", 0)

    def apply(self, tool_name: str, arguments: dict[str, Any]) -> None:
        result = self._env.call_tool(tool_name, arguments)
        if not result.ok:
            raise RuntimeError(result.error_message or result.error_type)

    def hashes(self) -> tuple[str, str]:
        try:
            state = self._env.get_final_state()
            return state["agent_db_hash"], state["user_db_hash"]
        finally:
            self._env.close()
