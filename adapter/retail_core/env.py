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
from pathlib import Path
from typing import Any

from adapter.retail_core import state
from adapter.retail_core.db import RetailDB
from adapter.retail_core.errors import INVALID_ARGUMENTS, TOOL_FAILURE
from adapter.retail_core.schemas import ToolResult
from adapter.retail_core.tools import TOOL_HANDLERS
from adapter.retail_core.trace import Trace


class RetailEnv:
    """data_dir must contain data/{users,orders,products}.json and
    cases/<case_id>.json (see verticals/retail/)."""

    def __init__(self, data_dir: str, seed: int = 42) -> None:
        self.data_dir = Path(data_dir)
        self.seed = seed
        self.db = RetailDB(self.data_dir / "data")
        self._cases_dir = self.data_dir / "cases"
        self._case: dict[str, Any] | None = None
        self._trace = Trace()

    def reset(self, case_id: str) -> dict[str, Any]:
        self.db.reset()
        self._case = self._load_case(case_id)
        self._trace = Trace()
        return {
            "case": state.agent_visible_case(self._case),
            "state": state.agent_visible_state(self.db),
        }

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            result = ToolResult(ok=False, error_code=INVALID_ARGUMENTS, error_message=f"unknown tool: {name}")
        else:
            try:
                result = handler(self.db, arguments)
            except Exception as exc:  # tool must never raise to the caller
                result = ToolResult(ok=False, error_code=TOOL_FAILURE, error_message=str(exc))
        self._trace.record(name, arguments, result)
        return result

    def get_trace(self) -> list[dict[str, Any]]:
        return self._trace.to_list()

    def get_final_state(self) -> dict[str, Any]:
        return state.agent_visible_state(self.db)

    def get_evaluator_view(self) -> dict[str, Any]:
        if self._case is None:
            raise RuntimeError("reset(case_id) must be called before get_evaluator_view()")
        return state.evaluator_view(self._case)

    def _load_case(self, case_id: str) -> dict[str, Any]:
        path = self._cases_dir / f"{case_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"no case fixture for case_id={case_id!r} at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
