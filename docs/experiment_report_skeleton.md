# Universal Agent Benchmark Experiment Report

This is the live, pilot-specific report scaffold for the controlled 60-case
experiment, not a reusable cross-experiment template. Public-safe owner names,
dates, and case counts may be filled here; sensitive freeze values and raw
evidence remain in the private execution record.

## Claim status

- Experiment ID: assigned in the private frozen execution record
- Formal experiment commit: the commit containing this report; exact SHA is
  retained in the private frozen execution record
- Protocol version: `pilot-60-v2.0`, prospectively frozen before the formal
  controlled-pilot execution; all v1.x attempts remain excluded
  `technical_smoke_only` evidence
- Gate status: `formal_scoring_complete_claims_review_pending`
- Freeze and review status: data/evaluator package approved by Chloe on
  2026-08-02/03 with final metric decisions on 2026-08-10; 24/24 fresh
  preflight and 228/228 formal result logical runs are complete. Chloe's 30 H5
  annotations are applied and the privacy boundary is confirmed. Claims review
  and downstream dashboard/report reconciliation remain pending.

The formal v2.0 execution passed the frozen-manifest, evaluator, environment,
and 24-run preflight gates before its result matrix started. Scoring is
complete; public aggregate tables and claims remain pending final review.

## Frozen configuration

| Item | Frozen value | Evidence |
|---|---|---|
| Model/provider/version | OpenAI-compatible provider; `gpt-4o-mini`; provider version unavailable | Private freeze record |
| Temperature/max output/seed | `0`; requested maximum output `4096`; requested seed `42`, recorded null/unsupported where unavailable | Private freeze record and run metadata |
| Run and token budgets | 24 preflights + 180 pilot + 48 repeats; usage recorded; no separate token cap | Protocol arithmetic |
| Case manifest and SHA-256 | `pilot-60-v1.0`, 60 cases; checksum retained privately | Owner freeze record |
| Evaluator versions and SHA-256 | H1/H2/H4/H5/E1/E2/E3 semantics 1.0; E5 semantics 0.3; checksums retained privately | Owner approvals |
| Framework/package versions | OpenAI Agents SDK 0.18.0; LangGraph 1.2.8; CrewAI 1.15.1; Python 3.12.13 | Environment validation record |
| Timeout | 300 seconds per attempt | Unified runner |
| Output root | Private `local-only` metrics directory | Freeze record |
| Rerun policy | One retry only for documented infrastructure failure; original attempt remains immutable | Attempt ledger |

These values were frozen for the v2.0 r10 execution. No v1.x attempt is reused
in the v2.0 gate or result denominators. The evaluator semantics remain
unchanged.

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
- E5 public output boundary (protocol v1.6): `result.final_state` reports only
  tool-observable `action_taken` and, for escalation, `escalation_reason`.
  Unavailable ticket IDs and order statuses are not requested from the model.
  The local replay evaluator remains authoritative.
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
- Join rule: each result records `logical_run_id`, `repeat`, and `attempt`;
  the append-only attempt ledger stores the matching result `run_id`. Reports
  retain distinct cases and repeats, select the latest attempt per logical run
  for aggregate analysis, and keep every attempt visible in the dashboard.

## Calibration / preflight

| Task | OpenAI Agents SDK | LangGraph | CrewAI | Gate |
|---|---|---|---|---|
| H1 | complete | complete | complete | passed |
| H2 | complete | complete | complete | passed |
| H4 | complete | complete | complete | passed |
| H5 | complete | complete | complete | passed |
| E1 | complete | complete | complete | passed |
| E2 | complete | complete | complete | passed |
| E3 | complete | complete | complete | passed |
| E5 | complete | complete | complete | passed |

Completed preflight logical runs: 8 tasks × 3 frameworks = 24. Documented,
policy-permitted infrastructure reruns remain separate attempts.

## Main experiment results

- Planned runs: 228 formal result logical runs.
- Completed logical runs: 228 (180 main + 48 targeted repeats).
- Errors and permitted reruns: retained in the private append-only evidence
  under the confirmed privacy boundary.
- Exclusions: all v1.x technical-smoke and v2.0 candidate-revision rows.
- Aggregate metrics: frozen locally after H5 aggregation; public tables remain
  pending claims review.
- Framework comparison: pending; no overall-winner claim is permitted.
- Figures: `scripts/generate_pilot_dashboard.py` defaults to a no-result
  placeholder. It can render an ignored local candidate only when supplied a
  matching allowlisted aggregate and privacy-confirmed freeze record; it
  rejects extra fields and does not expose the private experiment ID. Claims
  approval and public-release authorization remain separate gates.

## Targeted repeats

- Selection rule and case IDs: the eight owner-approved representative IDs in
  `docs/representative_case_ids.md`, with repeats 2 and 3 selected explicitly.
- Planned/completed runs: 48/48 additional repeat logical runs.
- Repeat outcomes: frozen locally; public interpretation remains pending
  claims review.

## Deviations and rerun ledger

Every post-freeze change receives a new version, reason, affected scope, owner
approval, and repeated preflight evidence. Original attempts remain immutable.

| Timestamp | Logical run | Attempt | Reason | Disposition | Artifact |
|---|---|---:|---|---|---|
| 2026-08-18 | Private formal E5 logical run | 2 | Attempt 1 reached the frozen user-simulator turn limit and was reviewed as infrastructure-eligible | Attempt 2 retained as the final row; it remained an error; no attempt 3 | Private append-only attempt ledger |

## Limitations and claim boundary

- **Protocol limitations:** This is a controlled 60-case pilot rather than a
  population benchmark. Only the eight owner-approved representative cases
  receive two additional observations; the other cases have one observation
  per framework. Stress testing and the deferred 400-case extension are not
  part of the formal denominator.
- **Evaluator limitations:** Metrics are task-specific and are not combined
  into a composite. H5 requires owner-reviewed human criterion annotations
  before deterministic aggregation. Exact full-case pass rules can obscure
  partially correct component behavior, so component metrics must retain their
  own definitions and denominators.
- **Provider/model limitations:** One agent model and one frozen generation
  configuration are used. The requested seed is recorded as unsupported where
  the provider does not expose an effective seed, so the targeted repeats are
  the observed stability evidence rather than proof of deterministic sampling.
- **E5 limitation:** E5 requires both public response-contract and local
  final-state replay criteria. The OpenAI Agents SDK E5 sweep is invalid under
  the frozen error-rate rule and cannot support a strong comparative claim;
  no attempt 3 or score rerun is permitted.
- **External validity:** The selected healthcare and e-commerce cases,
  provider, model, framework versions, and pinned retail simulator bound the
  findings. The pilot does not establish an overall best framework, complete
  robustness, production safety, or generalization to other models and tools.

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
