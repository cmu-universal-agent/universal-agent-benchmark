# WS3 Retail Wrapper Methodology and Limitations

Status: technical-validation protocol
Contract: tau-retail `0.2.0`
Scope: LangGraph, OpenAI Agents SDK, and CrewAI retail wrappers

## Purpose

WS3 tests whether three framework-native wrappers can expose the same stateful
retail tools while preserving one shared execution contract. It is an
integration and parity check. It does not measure which framework is better,
and its synthetic outputs are not benchmark scores.

## Methodology

### Controlled interface

All wrappers use `tools/tau_retail_contract.json` as the source of truth for
the 16 canonical tool names and input schemas. Each wrapper:

1. creates a fresh `RetailEnv` and calls `reset` exactly once with a unique
   reset ID;
2. registers the case's allowed tools through the framework's native tool
   layer;
3. forwards tool arguments to `RetailEnv.call_tool` without implementing
   retail business logic in the wrapper;
4. returns the shared core's structured result to the agent;
5. attaches the canonical tool trace and bounded final-state record to the
   common `AgentRunResult`; and
6. records framework/model metadata, effective generation settings, latency,
   and provider-reported token usage when available.

The same public synthetic case, retail data snapshot, seed, and canonical core
are used for offline wrapper validation. Reset is simulator lifecycle and is
never exposed as an agent tool.

### Offline evidence gate

Each real wrapper builds in-memory evidence for seven scenarios:

- no tool call;
- successful read;
- successful mutation;
- invalid arguments;
- disallowed tool;
- injected tool failure followed by one linked successful retry; and
- duplicate mutation rejection.

Together these scenarios contain eight tool attempts. The validator checks the
16-tool registry, deterministic reset, schema validity, allowed-tool and
argument flags, contiguous trace order, retry linkage, state-hash transitions,
mutation counts, canonical errors, and evaluator-data leakage.

Evidence is generated inside each framework's pinned environment and written
only to an ignored or temporary path. A three-framework parity check uses:

```text
python scripts/validate_ws3_tau_retail_contract.py \
  --wrapper-evidence <langgraph-evidence.json> \
  --wrapper-evidence <openai-evidence.json> \
  --wrapper-evidence <crewai-evidence.json>
```

The required terminal result includes `wrapper_evidence=3`. Generated raw
evidence JSON is not committed.

### Live-run boundary

A live retail run adds model planning and framework tool selection on top of
the same `RetailEnv`. Model, provider, temperature, output-token limit, seed,
prompt version, and experiment ID must be recorded for controlled comparisons.
Offline evidence must pass before any authorized live model run.

Formal E5 scoring is a separate step governed by the approved E5 run policy.
The public `RETAIL-E5-001` case is a `synthetic_fixture`, not formal E5 input.

## Exclusions

WS3 wrapper evidence does not include:

- framework rankings, accuracy claims, or statistical comparisons;
- formal E5 cases, evaluator-only gold, or private replay results;
- live-provider reliability, cost, or rate-limit evaluation;
- the full stress-testing matrix;
- multi-agent delegation, memory, human-in-the-loop flows, or concurrent
  sessions; or
- clinical or ecommerce benchmark conclusions from the earlier verticals.

## Privacy and publication boundary

Wrappers can access only agent-visible case input and shared tool results. They
must never call `RetailEnv.get_evaluator_view()` or
`RetailEnv.get_session_evidence()` during a normal agent run. The latter is
used only by the offline contract validator.

Raw formal E5 cases, gold actions, expected final states, source snapshots,
hashes, raw traces, and replay output remain outside Git. Public artifacts may
contain only allowlisted trace summaries and aggregate verdicts. The bounded
final-state record contains counts and a state hash, not raw customer, order,
product, rubric, or expected-action data.

## Known limitations

- The offline gate uses one small synthetic fixture and seven engineered
  scenarios. It demonstrates contract conformance, not task diversity or
  real-world effectiveness.
- Offline evidence invokes framework-native tool objects directly. It does not
  exercise model reasoning, tool choice, prompt sensitivity, or the complete
  provider request path.
- The invalid-argument fixture covers a missing required field. Other malformed
  types may be rejected or coerced by a framework's native argument layer
  before reaching the shared core and require separate live integration tests.
- The deterministic local simulator cannot represent upstream service
  variability, network faults, rate limits, or concurrent external mutations.
- Token usage is provider-reported and may be absent or differ in accounting
  across framework/provider versions. Latency includes local wrapper overhead
  and is sensitive to machine and network conditions.
- Generation-setting support depends on the selected model and provider.
  Unsupported settings are recorded, so runs with different effective settings
  must not be treated as controlled comparisons.
- Results apply to the pinned framework and dependency versions. Upgrades can
  change tool schemas, validation, retries, usage reporting, or execution
  behavior and require the offline gate to be rerun.
- All three wrappers share the same core, fixtures, and evaluator. This reduces
  integration confounds but can also hide defects shared by that common code.
- No formal sample-size, repeated-run, confidence-interval, or significance
  analysis is part of WS3 technical validation.

Until the three-framework evidence gate and an authorized controlled run both
pass, all WS3 outputs must remain labeled **synthetic technical validation,
not benchmark scores**.
