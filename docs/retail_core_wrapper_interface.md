# Retail core: wrapper integration interface (v0, pre-contract-freeze)

Owner: Xiaoxia (WS3, shared core). Consumers: CrewAI (Mickey), LangGraph
(Chloe), OpenAI Agents SDK (Lanfang).

`adapter/retail_core/env.py` (`RetailEnv`) is the **only** object a
framework wrapper drives for the retail vertical. Tool names below
(`get_user`, `get_order`, `get_product`, `refund_order`, `exchange_item`,
`return_item`, `escalate_to_human`) are placeholders pending Jessica's
canonical contract v1 — everything else (call shape, error handling,
trace/final-state read points) should not change when names do.

## Signatures

```python
class RetailEnv:
    def __init__(self, data_dir: str, seed: int = 42) -> None: ...
    def reset(self, case_id: str) -> dict: ...          # call once per run
    def call_tool(self, name: str, arguments: dict) -> ToolResult: ...
    def get_trace(self) -> list[dict]: ...               # after the run
    def get_final_state(self) -> dict: ...                # after the run
    def get_evaluator_view(self) -> dict: ...             # NEVER call this from a wrapper

@dataclass
class ToolResult:
    ok: bool
    data: dict | None = None
    error_code: str | None = None      # invalid_arguments | disallowed_action | tool_failure | duplicate_mutation
    error_message: str | None = None
    state_changed: bool = False
```

## Rules for wrappers

1. Call `env.reset(case_id)` exactly once per run, before the agent starts.
2. Register each canonical tool as a native framework tool whose body does
   exactly:
   ```python
   result = env.call_tool(name, arguments)
   return dataclasses.asdict(result)   # what the agent sees
   ```
   No business logic, no extra validation, no retries in the wrapper. If
   you find yourself writing an `if` beyond forwarding, that logic belongs
   in `adapter/retail_core/tools.py`, not the wrapper.
3. `call_tool` never raises for a business/validation failure — it always
   returns `ToolResult(ok=False, error_code=..., ...)`. Do not wrap the
   call in a try/except to catch business errors; only a wrapper bug should
   produce an uncaught exception here.
4. After the agent finishes, call `env.get_trace()` and
   `env.get_final_state()` and attach both to the run result as-is — do not
   reshape or subset them in the wrapper.
5. Never call `env.get_evaluator_view()`. It returns case gold (required
   actions, expected final state) and exists only for the evaluator.

## Reference wrapper stub (15 lines)

```python
from adapter.retail_core.env import RetailEnv
import dataclasses

env = RetailEnv(data_dir="verticals/retail", seed=42)

def make_tool(name: str):
    def tool_fn(**arguments):
        result = env.call_tool(name, arguments)
        return dataclasses.asdict(result)
    return tool_fn

def run_case(case_id: str, agent_run_fn):
    env.reset(case_id)
    agent_run_fn(tools={name: make_tool(name) for name in TOOL_NAMES})
    return {"trace": env.get_trace(), "final_state": env.get_final_state()}
```

## Running the offline tests

No model calls, no network, pure stdlib:

```
python3 -m unittest discover -s tests/retail_core -t .
```

or, from repo root, `python3 -m pytest tests/retail_core -q` (the plain
`pytest` binary won't put the repo root on `sys.path`; use `python3 -m
pytest` instead).
