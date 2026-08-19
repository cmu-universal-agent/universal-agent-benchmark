# Retail core: wrapper integration interface (v1, WS3 contract 0.2.0)

Owner: Xiaoxia (WS3, shared core). Consumers: CrewAI (Mickey), LangGraph
(Chloe), OpenAI Agents SDK (Lanfang).

`adapter/retail_core/env.py` (`RetailEnv`) is the **only** object a
framework wrapper drives for the retail vertical. Tool names, the reset
lifecycle, the structured error taxonomy, and the bounded state-evidence
shape below are pinned by `tools/tau_retail_contract.json` /
`docs/ws3_tau_retail_contract.md` (WS3 canonical contract, candidate for
owner review) — do not rename, reshape, or add ad hoc fields without a
contract-version update there first.

## Signatures

```python
class RetailEnv:
    def __init__(self, data_dir: str, seed: int = 42) -> None: ...
    def reset(self, case_id: str, reset_id: str, seed: int | None = None) -> dict: ...  # call once per run
    def call_tool(self, name: str, arguments: dict, *, retry_of: str | None = None) -> ToolResult: ...
    def get_trace(self) -> list[dict]: ...                # after the run; tool_call.schema.json records
    def get_final_state(self) -> dict: ...                 # after the run; bounded state record
    def get_session_evidence(self, fixture_id: str) -> dict: ...  # EVALUATOR-ONLY, see below
    def get_evaluator_view(self) -> dict: ...              # NEVER call this from a wrapper

@dataclass
class ToolResult:
    ok: bool
    data: dict | None = None
    error_type: str | None = None      # one of the 9 canonical error_type values, see the contract's error table
    error_message: str | None = None
    state_changed: bool = False
```

The 16 canonical tool names (`calculate`, `cancel_pending_order`,
`exchange_delivered_order_items`, `find_user_id_by_email`,
`find_user_id_by_name_zip`, `get_item_details`, `get_order_details`,
`get_product_details`, `get_user_details`, `list_all_product_types`,
`modify_pending_order_address`,
`modify_pending_order_items`, `modify_pending_order_payment`,
`modify_user_address`, `return_delivered_order_items`,
`transfer_to_human_agents`) and their input schemas live in
`tools/tau_retail_contract.json` / `tools/schemas/*.schema.json` — read
those, not this doc, for the authoritative argument shapes.

## Rules for wrappers

1. Call `env.reset(case_id, reset_id, seed)` exactly once per run, before
   the agent starts. `reset_id` must be unique per run (e.g. a UUID) —
   never reuse one across runs, so state evidence from different resets is
   never mixed.
2. Register each canonical tool as a native framework tool whose body does
   exactly:
   ```python
   result = env.call_tool(name, arguments)
   return dataclasses.asdict(result)   # what the agent sees
   ```
   No business logic, no extra validation, no retries in the wrapper. If
   you find yourself writing an `if` beyond forwarding, that logic belongs
   in `adapter/retail_core/tools.py`, not the wrapper. If the agent
   explicitly retries a tool call and the wrapper happens to know the prior
   `tool_call_id` (from `env.get_trace()[-1]["tool_call_id"]`), it may pass
   it as `retry_of` — this is optional and most wrappers can ignore it.
3. `call_tool` never raises for a business/validation failure — it always
   returns `ToolResult(ok=False, error_type=..., ...)`. Do not wrap the
   call in a try/except to catch business errors; only a wrapper bug should
   produce an uncaught exception here.
4. After the agent finishes, call `env.get_trace()` and
   `env.get_final_state()` and attach both to the run result as-is — do not
   reshape or subset them in the wrapper. Both are already bounded/
   schema-conformant; `get_final_state()` never contains raw user/order/
   product records, only counts + a state hash (raw database state is
   evaluator-only, per the contract doc).
5. Never call `env.get_evaluator_view()` or `env.get_session_evidence()`
   from a wrapper. `get_evaluator_view()` returns case gold (required
   actions, expected final state) and exists only for the evaluator.
   `get_session_evidence()` binds per-call state-before/after hashes for
   contract validation (see `scripts/validate_ws3_tau_retail_contract.py
   --wrapper-evidence`) and is not part of a normal run.

## Reference wrapper stub

```python
import uuid
import dataclasses
from adapter.retail_core.env import RetailEnv

env = RetailEnv(data_dir="verticals/retail", seed=42)

def make_tool(name: str):
    def tool_fn(**arguments):
        result = env.call_tool(name, arguments)
        return dataclasses.asdict(result)
    return tool_fn

def run_case(case_id: str, agent_run_fn):
    env.reset(case_id, reset_id=f"run-{uuid.uuid4().hex}", seed=42)
    agent_run_fn(tools={name: make_tool(name) for name in TOOL_NAMES})
    return {"trace": env.get_trace(), "final_state": env.get_final_state()}
```

## Running the offline tests

No model calls, no network, pure stdlib plus `jsonschema`:

```
python3 -m unittest discover -s tests/retail_core -t .
```

or, from repo root, `python3 -m pytest tests/retail_core -q` (the plain
`pytest` binary won't put the repo root on `sys.path`; use `python3 -m
pytest` instead).

`tests/retail_core/test_contract_conformance.py` additionally drives a real
`RetailEnv` through the seven required fixture scenarios and validates the
resulting evidence with `scripts/validate_ws3_tau_retail_contract.py
--wrapper-evidence` — the same check a real wrapper's own offline evidence
must pass before it's considered contract-conformant.
