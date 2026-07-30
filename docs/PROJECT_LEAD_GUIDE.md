# Universal Agent Benchmark - Project Lead Guide

Last verified: 2026-07-30 (Asia/Shanghai)

## Purpose

Use this file to resume project coordination from current repository and
GitHub evidence. It records durable status, ownership, gates, privacy
boundaries, and safe next actions. Mutable PR and branch state must still be
checked on GitHub.

## Source of truth

Use evidence in this order:

1. official GitHub state and explicit review comments;
2. code, schemas, tests, and validation evidence at that verified commit;
3. dated decisions from the responsible owner;
4. this guide;
5. historical workstream documents and meeting notes;
6. downloaded attachments, archived chats, and recollection.

Treat `draft`, `proposal`, `pending_approval`, and `preliminary` as non-final.
Separate infrastructure validation, synthetic demo, technical smoke, formal
replay, and benchmark results.

## Canonical repository state

- Official repository:
  <https://github.com/cmu-universal-agent/universal-agent-benchmark>
- Verified `main`: `4bf4ef4a9147fbfbf3504a3e4cce258ce2088fdc`.
- PRs #14, #15, #17, #18, #19, #21, and #22 are merged.
- PRs #13 and #16 were closed without merge after their useful work was
  superseded or consolidated.
- Canonical local checkout:
  `C:\Users\Jessica\Documents\Universal Agent\universal-agent-benchmark-git`.
- The canonical local checkout is clean but behind GitHub `main`; fast-forward
  it before starting new work. Historical feature worktrees are not current
  repository state.

Never resume formal work from an old clone or dirty feature branch. Start from
the GitHub-verified `main` and use one clean worktree per active PR.

## Workstream status

| Workstream | Verified state |
|---|---|
| WS1 - scope and task selection | Complete |
| WS2 - infrastructure and dataset preparation | Complete and merged |
| WS3 - shared retail evaluation | Complete: three real wrappers and parity gate passed |
| WS4 - formal experiments | Not started; current outputs are engineering validation |
| WS5 - analysis and final report | Not started as a formal workstream |

## WS3 completed on `main`

- Canonical tau-retail contract v0.2.0 with 16 tools and unified reset, state,
  error, trace, and final-state schemas.
- Deterministic shared `RetailEnv` core and contract fixtures.
- Real LangGraph wrapper with framework-native tool registration and
  schema-valid offline wrapper evidence.
- Real OpenAI Agents SDK wrapper from PR #18 with all 16 tools registered as
  `FunctionTool` objects and schema-valid offline wrapper evidence.
- Real CrewAI wrapper from PR #22 with all 16 tools registered as native
  `BaseTool` objects and schema-valid offline wrapper evidence.
- LangGraph and OpenAI invalid-argument paths reach the shared core and emit
  canonical rejected traces.
- Three-framework parity validation passed with `wrapper_evidence=3`.
- Methodology and limitations are documented in
  `docs/ws3_methodology_and_limitations.md`.
- Public-safe E5 evaluator, conversion, smoke, and pinned replay plumbing.
- Private formal E5 replay completed twice with byte-identical output for all
  four approved cases.
- Synthetic offline demo harness at `scripts/demo_ws3_offline.py`.
- Public dashboard generator with aggregate-only, allowlisted output.
- The old static dashboard prototype and its detailed simulated OpenAI/CrewAI
  rows were removed in PR #17.
- Dashboard evidence status:
  - LangGraph: `available`
  - OpenAI Agents SDK: `available`
  - CrewAI: `available`

Current real wrapper count is 3/3. Shared-core evidence is not framework
evidence, and synthetic demo output is not a benchmark score.

## WS3 gate result

PR #22 supplied the CrewAI wrapper, matching offline evidence, focused tests,
and the methodology/limitations record. A clean Python 3.12 validation across
LangGraph, OpenAI Agents SDK, and CrewAI passed the shared contract validator
with `wrapper_evidence=3`. Raw evidence remained local and was deleted after
validation.

## Wrapper evidence gate

A wrapper counts only when it:

1. is merged on the GitHub-verified `main`;
2. registers all 16 tools through the framework-native tool layer;
3. forwards tool execution to the shared core without duplicating business
   logic;
4. produces schema-valid trace and final-state evidence;
5. passes the shared offline evidence validator;
6. does not publish generated raw evidence JSON.

Do not count a pending branch, expected same-day delivery, wrapper skeleton, or
direct shared-core invocation as framework evidence. Update dashboard framework
status independently after each wrapper satisfies this gate.

## E5 decisions and replay

Chloe approved the four owner-reviewed E5 case/gold records and the v0.3
response/final-state policy:

- pass only when Criterion A and Criterion B both hold and no failure class is
  detected;
- retry a harness/runtime error exactly once;
- invalidate a framework sweep when more than 5 percent of final attempts are
  errors;
- record upstream DB-only comparison under `run_log.sanity.tau3_db`;
- treat `compare_args=[]` as tool-name presence only;
- treat `compare_args=null` as comparison of all arguments;
- treat `verticals/retail/cases/RETAIL-E5-001.json` as a public
  `synthetic_fixture`, never formal E5 input.

The private replay pinned and verified its source and retail snapshot, checked
task/action identity and schemas, hard-failed on action exceptions, wrote
atomically, and produced byte-identical output on an independent rerun.

Keep these local unless explicit publication approval says otherwise:

- raw E5 cases and gold actions;
- evaluator-only response/final-state contracts;
- source snapshots and contents;
- initial and expected hashes;
- replay output and raw traces;
- dedicated replay environments.

Current local-only replay locations:

- `C:\Users\Jessica\Documents\Universal Agent\tmp\e5-approved-20260729`
- `C:\Users\Jessica\Documents\Universal Agent\tmp\tau2-bench-replay-1d244f5`
- `C:\Users\Jessica\Documents\Universal Agent\tmp\.venv-e5-replay`

## Ownership and next actions

| Area | Owner | Reviewer | Next action |
|---|---|---|---|
| Canonical contract and cross-framework integration | Jessica | Framework owner | Protect the completed 16-tool and 3/3 wrapper parity gate |
| E5 semantics and gold | Chloe | Jessica for integration/privacy | Review only if public evaluator semantics change |
| Shared retail core | Xiaoxia | Jessica | Maintain contract regressions |
| CrewAI WS3 wrapper | Mickey | Jessica/Xiaoxia | Maintain the merged wrapper and evidence |
| Methodology and limitations | Mickey | Team | Maintain the merged protocol record |
| Dashboard evidence states | Jessica/Xiaoxia | Framework owner | Keep all three availability states aligned with verified evidence |

Jessica may implement infrastructure, approved deterministic conversion,
privacy checks, schemas, validators, replay plumbing, and cross-framework
integration. Jessica must not invent or revise another owner's gold semantics
or publish benchmark conclusions from technical smoke evidence.

## Demo boundary

The meeting demo is synthetic technical validation:

1. run the single-command offline harness;
2. show the 16-tool contract and deterministic reset;
3. show read, mutation, invalid-argument, disallowed-action, duplicate-action,
   tool-failure, and leakage controls;
4. show only sanitized trace summaries and aggregate final-state verdicts;
5. state that all three frameworks have real offline wrapper evidence and the
   combined parity gate passed.

Do not expose evaluator-only gold or present the demo as a benchmark score,
framework ranking, or live E5 result.

## Clean execution policy

Before a formal replay, smoke, or experiment:

1. verify GitHub `main` and fast-forward the clean canonical checkout;
2. create a fresh worktree for the exact PR or experiment commit;
3. create a fresh virtual environment from that commit's pinned requirements;
4. record commit, dependency source, experiment ID, and scoring label;
5. run deterministic offline checks before any authorized model call;
6. keep raw outputs and evaluator-only data outside Git.

For stale or stacked wrapper PRs, rebuild from current `main` and transplant
only the wrapper, tests, and in-memory evidence builder. Do not carry old
README, shared-core, schema, dataset, other-framework, or generated evidence
JSON changes.

## Validation

Core checks do not require live model calls:

```powershell
python .\scripts\validate_contract_fixtures.py
python .\scripts\validate_adapter_contracts.py
python .\scripts\validate_shared_tool_contracts.py
python .\scripts\validate_ws3_tau_retail_contract.py
python -m unittest discover -s .\tests\retail_core -p "test_*.py"
python .\scripts\demo_ws3_offline.py
```

Framework-specific evidence must run in that framework's fresh pinned
environment. Never run live model calls merely to refresh status.

## Publishing rules

Before publishing:

1. inspect the exact diff and stage named files only;
2. run checks proportional to the change;
3. push to `official`, not the personal `origin`;
4. verify PR head, base, changed-file list, mergeability, reviews, and checks;
5. keep preliminary outputs labelled `not benchmark scores`.

Never publish `.env`, credentials, virtual environments, raw dataset caches,
evaluator-only gold, snapshots, hashes, replay outputs, raw traces, generated
metrics, or detailed simulated framework rows.
