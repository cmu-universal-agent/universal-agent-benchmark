# Universal Agent Benchmark Experiment Report

This is the live, pilot-specific report scaffold for the controlled 60-case
experiment, not a reusable cross-experiment template. Public-safe owner names,
dates, and case counts may be filled here; sensitive freeze values and raw
evidence remain in the private execution record.

## Claim status

- Experiment ID: assigned in the private frozen execution record
- Formal experiment commit: the commit containing this report; exact SHA is
  retained in the private frozen execution record
- Protocol version: `pilot-60-v1.1`; case/gold/evaluator semantics are
  unchanged from v1.0, and only the E5 user-simulator transmission allowlist
  changed
- Gate status: `technical_smoke_only`
- Freeze timestamp and approver: data/evaluator package approved by Chloe on
  2026-08-02/03 with final metric decisions on 2026-08-10; full Experiment
  Ready gate remains open until all 24 preflights pass

No result may be described as a formal benchmark unless the frozen-manifest,
evaluator, environment, and 24-run preflight gates all passed before execution.

## Frozen configuration

| Item | Frozen value | Evidence |
|---|---|---|
| Model/provider/version | OpenAI-compatible provider; `gpt-4o-mini`; provider version unavailable | Private freeze record |
| Temperature/max output/seed | `0`; provider defaults where unsupported/unexposed | Private freeze record and run metadata |
| Run and token budgets | 24 preflights + 180 pilot + 48 repeats; usage recorded; no separate token cap | Protocol arithmetic |
| Case manifest and SHA-256 | `pilot-60-v1.0`, 60 cases; checksum retained privately | Owner freeze record |
| Evaluator versions and SHA-256 | H1/H2/H4/H5/E1/E2/E3 semantics 1.0; E5 semantics 0.3; checksums retained privately | Owner approvals |
| Framework/package versions | OpenAI Agents SDK 0.18.0; LangGraph 1.2.8; CrewAI 1.15.1; Python 3.12.13 | Environment validation record |
| Timeout | 300 seconds per attempt | Unified runner |
| Output root | Private `local-only` metrics directory | Freeze record |
| Rerun policy | One retry only for documented infrastructure failure; original attempt remains immutable | Attempt ledger |

These are candidate execution values until the formal code commit and 24
preflights are frozen. Chloe closed the remaining metric decisions on
2026-08-10.

## Architecture and implementation

- Unified runner: resolves a frozen case set once, invokes each framework in
  its pinned Python environment, records append-only attempts, and evaluates
  only results created by the current invocation.
- Shared E5 routing: the task loader maps generated `vertical="ecommerce"`
  E5 cases to the canonical `retail` wrapper route once, before framework
  dispatch. All three wrappers therefore receive the same 16-tool contract.
- E5 response-contract evaluator: checks required and forbidden response
  content under the owner-approved v0.3 matching policy.
- E5 final-state replay: independently applies the approved gold actions and
  observed successful tool calls to pinned simulator instances, then compares
  agent and user database hashes. Response and state criteria must both pass.
- E5 privacy boundary: only `user_simulator.task_instructions` and the pinned
  simulator controls required to generate the customer turn may enter the
  OpenAI user-simulator request. Response contracts, gold actions, rubrics,
  expected state, and hashes remain local.
- Deterministic metrics: H1 exact decision plus common structured evidence,
  confidence, and safety fields; H2 urgency, under-triage, escalation, and
  safety; H4 per-field precision/recall/F1; E1 trend direction; E2 ranked IDs
  plus constraints; E3 policy decision. H5 exact boundary action and safe
  refusal are implemented. H5 uses owner-approved human criterion annotation
  followed by deterministic `h5-scoring-rule-v1` aggregation.

## Reproducibility

- Environment build and validation commands: install each framework's pinned
  requirements into its dedicated Python 3.12 environment, run `pip check`,
  framework wrapper tests, the combined wrapper-evidence validator, the
  60-case validator, and list-only runner before any model call.
- Python and package versions: Python 3.12.13 with the framework versions in
  the frozen-configuration table.
- Manifest/gold isolation: agent-visible cases and evaluator-only gold are
  loaded from separate private paths. Gold, raw traces, private snapshots,
  and hashes are excluded from Git and public dashboard artifacts.
- Randomness controls: manifest selection seed is fixed; the retail simulator
  reset seed is fixed; unsupported provider seeds remain null and are recorded
  as such rather than simulated.
- Artifact inventory: frozen manifest, owner approvals, evaluator versions,
  environment record, run outputs, append-only attempt ledger, aggregate
  tables, report, and dashboard reconciliation evidence.

## Calibration / preflight

| Task | OpenAI Agents SDK | LangGraph | CrewAI | Gate |
|---|---|---|---|---|
| H1 | | | | |
| H2 | | | | |
| H4 | | | | |
| H5 | | | | |
| E1 | | | | |
| E2 | | | | |
| E3 | | | | |
| E5 | | | | |

Expected attempts: 8 tasks × 3 frameworks = 24, excluding documented,
policy-permitted infrastructure reruns.

## Main experiment results

- Planned runs:
- Completed logical runs:
- Errors and permitted reruns:
- Exclusions:
- Aggregate metrics:
- Framework comparison:

## Targeted repeats

- Selection rule and case IDs:
- Planned/completed runs:
- Repeat outcomes:

## Deviations and rerun ledger

Every post-freeze change receives a new version, reason, affected scope, owner
approval, and repeated preflight evidence. Original attempts remain immutable.

| Timestamp | Logical run | Attempt | Reason | Disposition | Artifact |
|---|---|---:|---|---|---|
| | | | | | |

## Limitations and claim boundary

- Protocol limitations:
- Evaluator limitations:
- Provider/model limitations:
- External-validity limitations:

## Technical-method appendix

### Case selection and gold

The controlled pilot contains 60 frozen cases: eight each for H1, H2, H4,
H5, E1, E2, and E3, plus four owner-approved E5 cases. Evaluator-only gold is
never included in agent prompts or public artifacts. Owner corrections are
versioned; later changes require a new manifest/evaluator version and affected
preflight reruns.

### Runner and framework parity

The unified runner dispatches the same resolved case to OpenAI Agents SDK,
LangGraph, and CrewAI subprocesses in isolated environments. Framework parity
requires framework-native registration of the same 16 retail tools and
schema-valid wrapper evidence; shared-core invocation alone does not count.

### Evaluator definitions

Content metrics are task-specific and reported separately rather than merged
into a composite score. Schema/instruction metrics are recorded alongside task
metrics. H5 free-text criteria receive human `met`/`not_met` annotations; the
approved rule then deterministically computes the normalized score and pass
verdict. Human annotations remain part of the private audit evidence.

### E5 simulator and state validation

Formal E5 uses the pinned private tau-retail source and replay environment.
Pass requires both response-contract and final-state criteria with no failure
class. A runtime/harness error receives at most one documented retry, and an
error rate above five percent invalidates the affected framework sweep.

### Environment lock and commands

Every formal run records framework, model, effective generation parameters,
timestamps, end-to-end latency, token usage when supplied, prompt/schema
versions, case identity, and experiment identity. Environment checks are
rerun after any dependency or formal-code change.

### Artifact checksums

Checksums for private cases, gold, replay state, and raw results remain in the
private freeze/evidence package. Public documentation records only versions,
counts, and aggregate-safe validation status.

### Failure taxonomy and adjudication

Model/evaluator failures remain distinct from provider, runner, timeout,
environment, and output-write failures. Only the latter infrastructure classes
permit a retry; low scores, wrong answers, or poor tool choices never do.
