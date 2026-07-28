# WS3 Tau-Retail Canonical Contract

Status: **candidate for owner review**
Contract version: `0.1.0`
Owner: Jessica
Scope: framework-neutral tool, reset, state-evidence, and error behavior

## Decision boundary

This contract freezes the integration surface that all three framework wrappers
must share. It does not implement the simulator, any framework wrapper, E5 gold
semantics, or stress variants.

- Xiaoxia owns the shared simulator/core implementation.
- Mickey, Chloe, and Lanfang own the CrewAI, LangGraph, and OpenAI Agents SDK
  wrappers respectively.
- Chloe owns evaluator-visible E5 success and final-state semantics.
- Lanfang's PR #3 failure taxonomy remains a draft. This contract uses compatible
  structured errors without adopting unapproved stress-schema fields.

## Frozen surface

`tools/tau_retail_contract.json` is the machine-readable source of truth. It
pins 15 assistant tools used by the local 114-task tau-retail cache and the
eight prepared E5 cases. Each tool has a Draft 2020-12 input schema under
`tools/schemas/`.

Wrappers must expose the canonical names directly. Business rules and state
mutation stay in the shared core; wrappers may only translate framework-native
call objects into the canonical request and normalize the response into
`schemas/tool_call.schema.json`.

## Lifecycle API

Reset is simulator lifecycle, not an agent-visible tool:

```text
reset(case_id, reset_id, seed) -> state record
execute(tool_name, arguments, allowed_tools) -> normalized tool call + state record
snapshot() -> state record
```

Required reset behavior:

1. Resetting the same case with the same seed must produce the same state hash.
2. Reset clears call order, retry linkage, injected failures, and mutation count.
3. Every run receives a new `reset_id`; state evidence from different resets
   must never be mixed.
4. Raw database state remains evaluator-only. Shared logs store the bounded
   evidence record defined by `schemas/tau_retail_state_record.schema.json`.
5. The complete reset/trace/final-state envelope must validate against
   `schemas/tau_retail_session_evidence.schema.json`.

## State and mutation evidence

Each tool attempt records `state_before_sha256` and `state_after_sha256` in the
evaluator-side session evidence fixture. The existing normalized tool-call
schema remains unchanged. Each session also records `allowed_tools`, allowing
the validator to derive `was_allowed` instead of trusting wrapper metadata.

- Read/non-mutating success: state hashes are equal.
- Successful mutation: hashes differ and mutation count increases once.
- Rejected, invalid, failed, or timed-out call: hashes are equal.
- Duplicate mutation: the second attempt returns `duplicate_action`, does not
  mutate state, and does not increment mutation count.

The bounded state record intentionally contains only collection counts, a
canonical state hash, sequence index, and mutation count. It contains no raw
customer, order, product, gold, rubric, or expected-action content.

## Structured errors

Wrappers map core failures to the existing `tool_call.error.error_type` field.
The allowed values and retry defaults are declared in the machine contract:

| Error type | Outcome | Retryable default | Meaning |
|---|---|---:|---|
| `invalid_arguments` | `rejected` | false | Input failed the canonical tool schema |
| `disallowed_tool` | `rejected` | false | Tool was absent from `allowed_tools` |
| `not_found` | `error` | false | Referenced entity does not exist |
| `invalid_state` | `error` | false | Operation is incompatible with current state |
| `duplicate_action` | `error` | false | A one-time mutation was attempted again |
| `policy_rejected` | `error` | false | Canonical retail rule rejected the action |
| `tool_failure` | `error` | true | Injected or transient tool failure |
| `timeout` | `timeout` | true | Call exceeded the shared timeout |
| `internal_error` | `error` | false | Unclassified core failure |

Error messages are diagnostic only. Evaluators and wrappers must branch on
`error_type`, never parse message text.

## Minimum offline fixtures

`tests/fixtures/tau_retail_contract_cases.json` is synthetic and contains no
tau-retail records. It covers:

- deterministic reset;
- no-tool and read-only state preservation;
- successful mutation;
- invalid arguments and disallowed tools;
- structured transient tool failure;
- duplicate mutation with exactly-once state change;
- evaluator-data leakage guard.

Run:

```powershell
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_ws3_tau_retail_contract.py"
```

Each wrapper must emit the envelope in
`schemas/tau_retail_wrapper_evidence.schema.json`. Validate real wrapper
evidence with:

```powershell
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_ws3_tau_retail_contract.py" `
  --wrapper-evidence ".\path\to\wrapper_evidence.json"
```

The same seven fixture IDs are required for every wrapper, so parity is checked
against one matrix rather than framework-specific test interpretations.

This validates only the shared contract. Passing it does not mean the simulator
or any wrapper has been implemented, E5 semantics approved, or benchmark scores
produced.

## Contract-only meeting demo

The deterministic meeting fallback uses only the synthetic contract fixtures:

```powershell
& ".\.venv-openai\Scripts\python.exe" ".\scripts\demo_ws3_offline.py" `
  --evidence-out ".\tmp\ws3-demo-evidence.json"
```

Expected output:

```text
WS3_OFFLINE_DEMO technical_validation_only=1 benchmark_scores=0
CONTRACT_OK version=0.1.0 tools=15
RESET_OK deterministic=1
READ_OK tool=get_order_details state_changed=0
WRITE_OK tool=modify_pending_order_payment mutation_count=1
DUPLICATE_OK tool=cancel_pending_order error=duplicate_action state_changed=0
EVIDENCE_OK scenarios=7 calls=8 leakage=0
```

Suggested six-minute flow: introduce the 15-tool contract, run the command,
explain the read/write/duplicate state transitions, open the sanitized evidence
JSON, and finish with the remaining core/wrapper integration gates. This is
contract evidence only, not a simulator, framework run, E5 semantic approval,
or benchmark result.

## Upstream provenance

The tool surface was reconciled on 2026-07-22 against:

- local tau-retail cache: 114 tasks, 15 unique expected action names;
- local prepared E5 cases: the same 15 `allowed_tools`;
- upstream `sierra-research/tau2-bench` retail toolkit at
  `src/tau2/domains/retail/tools.py`, blob
  `eba01ab32dca0d4ef33328c22358b794d859f2b6`.

Upstream currently also exposes `list_all_product_types`, but it is outside the
frozen MVP surface because neither the local task action set nor prepared E5
cases require it. Adding it requires a contract-version update.
