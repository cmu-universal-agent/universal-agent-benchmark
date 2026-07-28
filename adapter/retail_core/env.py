"""RetailEnv: the single stateful object every framework wrapper drives.

No framework imports here (see AGENTS.md: framework integrations must
remain thin wrappers, and comparable frameworks must use the same shared
environment). CrewAI/LangGraph/OpenAI-Agents-SDK wrappers should each
register the canonical tools as native framework tools whose body does
exactly:

    result = env.call_tool(name, arguments)
    return serialize(result)  # asdict(result), see docs/retail_core_wrapper_interface.md

No business logic belongs in a wrapper.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adapter.retail_core import errors, state
from adapter.retail_core.db import RetailDB
from adapter.retail_core.schemas import ToolResult
from adapter.retail_core.tools import TOOL_HANDLERS
from adapter.retail_core.trace import Trace
from adapter.validation import validate_tool_arguments

CONTRACT_VERSION = "0.1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RetailEnv:
    """data_dir must contain data/{users,orders,products}.json and
    cases/<case_id>.json (see verticals/retail/)."""

    def __init__(self, data_dir: str, seed: int = 42) -> None:
        self.data_dir = Path(data_dir)
        self.seed = seed
        self.db = RetailDB(self.data_dir / "data")
        self._cases_dir = self.data_dir / "cases"
        self._case: dict[str, Any] | None = None
        self.case_id: str | None = None
        self.reset_id: str | None = None
        self.allowed_tools: frozenset[str] = frozenset()
        self._trace = Trace(run_id=f"run-{uuid.uuid4().hex}")
        self._initial_state: dict[str, Any] | None = None

    def reset(self, case_id: str, reset_id: str, seed: int | None = None) -> dict[str, Any]:
        """Lifecycle call, not an agent-visible tool (see contract doc).

        ``reset_id`` is supplied by the caller (one per run) so state
        evidence from different resets is never mixed, per
        docs/ws3_tau_retail_contract.md's lifecycle rule #3. The fixture
        data here carries no randomness, so ``seed`` only affects the
        recorded state record, never the resulting state itself -- the same
        case+seed reset is deterministic by construction.
        """
        if seed is not None:
            self.seed = seed
        self.db.reset()
        self._case = self._load_case(case_id)
        self.case_id = case_id
        self.reset_id = reset_id
        self.allowed_tools = frozenset(self._case.get("allowed_tools", []))
        self._trace = Trace(run_id=f"run-{uuid.uuid4().hex}")
        self._initial_state = self.db.state_record(
            reset_id=reset_id, case_id=case_id, sequence_index=0
        )
        return {
            "case": state.agent_visible_case(self._case),
            "state": dict(self._initial_state),
        }

    def call_tool(
        self, name: str, arguments: dict[str, Any], *, retry_of: str | None = None
    ) -> ToolResult:
        """``retry_of`` is optional and only for a caller that already knows
        this call repeats an earlier ``tool_call_id`` (e.g. an agent retrying
        after a ``tool_failure``); the default wrapper stub in
        docs/retail_core_wrapper_interface.md never needs to pass it. Read
        the id to retry from ``env.get_trace()[-1]["tool_call_id"]``."""
        if self._case is None:
            raise RuntimeError("reset(case_id, reset_id, seed) must be called before call_tool()")

        started_at = _utc_now()
        started_perf = time.perf_counter()
        state_before = self.db.state_sha256()

        was_allowed = name in self.allowed_tools
        argument_errors = validate_tool_arguments(name, arguments)
        arguments_valid = not argument_errors

        if not was_allowed:
            result = ToolResult(
                ok=False,
                error_type=errors.DISALLOWED_TOOL,
                error_message=f"tool not in allowed_tools for this case: {name}",
            )
        elif not arguments_valid:
            result = ToolResult(
                ok=False,
                error_type=errors.INVALID_ARGUMENTS,
                error_message="; ".join(argument_errors),
            )
        else:
            handler = TOOL_HANDLERS[name]
            try:
                result = handler(self.db, arguments)
            except Exception as exc:  # a handler bug must never raise to the caller
                result = ToolResult(ok=False, error_type=errors.INTERNAL_ERROR, error_message=str(exc))

        state_after = self.db.state_sha256()
        completed_at = _utc_now()
        latency_ms = max(0, int((time.perf_counter() - started_perf) * 1000))

        if result.ok:
            outcome, error_record = "success", None
        else:
            outcome = errors.outcome_for(result.error_type)
            error_record = {
                "error_type": result.error_type,
                "message": result.error_message or result.error_type,
                "retryable": errors.retryable_default(result.error_type),
            }

        self._trace.record(
            tool_name=name,
            arguments=arguments,
            was_allowed=was_allowed,
            arguments_valid=arguments_valid,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            outcome=outcome,
            result=result.data if outcome == "success" else None,
            error=error_record,
            state_before_sha256=state_before,
            state_after_sha256=state_after,
            retry_of=retry_of,
        )
        return result

    def get_trace(self) -> list[dict[str, Any]]:
        """schemas/tool_call.schema.json-conformant records; attach as-is."""
        return self._trace.to_tool_calls()

    def get_final_state(self) -> dict[str, Any]:
        """Bounded evidence (schemas/tau_retail_state_record.schema.json).

        Deliberately never the raw users/orders/products dump: per
        docs/ws3_tau_retail_contract.md, "raw database state remains
        evaluator-only."
        """
        return self.db.state_record(
            reset_id=self.reset_id, case_id=self.case_id, sequence_index=len(self._trace)
        )

    def get_session_evidence(self, fixture_id: str) -> dict[str, Any]:
        """schemas/tau_retail_session_evidence.schema.json envelope.

        Evaluator-only: binds the initial/final bounded state to the
        per-call state_before/after hashes so a reviewer (or
        scripts/validate_ws3_tau_retail_contract.py) can verify duplicate
        mutation and read/write invariants without ever seeing raw state.
        """
        if self._initial_state is None:
            raise RuntimeError("reset(case_id, reset_id, seed) must be called before get_session_evidence()")
        return {
            "fixture_id": fixture_id,
            "allowed_tools": sorted(self.allowed_tools),
            "initial_state": dict(self._initial_state),
            "events": self._trace.to_session_events(),
            "final_state": self.get_final_state(),
        }

    def get_evaluator_view(self) -> dict[str, Any]:
        if self._case is None:
            raise RuntimeError("reset(case_id, reset_id, seed) must be called before get_evaluator_view()")
        return state.evaluator_view(self._case)

    def _load_case(self, case_id: str) -> dict[str, Any]:
        path = self._cases_dir / f"{case_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"no case fixture for case_id={case_id!r} at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
