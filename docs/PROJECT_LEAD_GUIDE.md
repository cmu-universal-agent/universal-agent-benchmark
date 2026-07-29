# Universal Agent Benchmark — Project Lead Guide

Last verified: 2026-07-29 (Asia/Shanghai)

## Purpose

Use this file to resume project coordination from current repository and
GitHub evidence. It records durable status, ownership, gates, privacy
boundaries, and the safest next actions. Mutable PR state must still be checked
on GitHub.

## Source of truth

Use evidence in this order:

1. current code, schemas, tests, and validation evidence;
2. official GitHub state and explicit review comments;
3. dated decisions from the responsible owner;
4. this guide;
5. historical workstream documents and meeting notes;
6. downloaded attachments, archived chats, and recollection.

Treat `draft`, `proposal`, `pending_approval`, and `preliminary` as non-final.
Do not infer benchmark results or owner approval from technical smoke evidence.

## Canonical repository state

- Official repository:
  <https://github.com/cmu-universal-agent/universal-agent-benchmark>
- Canonical local checkout:
  `C:\Users\Jessica\Documents\Universal Agent\universal-agent-benchmark-git`
- Verified `main`: `07d87a8567ec5f7d9c3826599773f8568a1142e8`
- The canonical checkout is clean, on `main`, and tracks `official/main`.
- PRs #1–#10, #12, #14, and #15 are merged. PR #11 was closed and
  superseded by #12.
- Merged/superseded local branches, remote-tracking refs, old worktrees,
  temporary downloads, and stale framework virtual environments were removed
  on 2026-07-29.
- Open PR worktrees are retained separately. Merged PR #14/#15 worktrees are
  preserved until their local changes and refs are audited.

Never resume formal work from an old clone or dirty feature branch. Start from
fresh `official/main` and create one separate worktree per active PR.

## Open pull requests

Verified on 2026-07-29:

| PR | Scope | State | Current gate |
|---|---|---|---|
| [#13](https://github.com/cmu-universal-agent/universal-agent-benchmark/pull/13) | Post-merge WS3 audit | Draft and mergeable; no reviews or checks | Confirm findings/owners, then mark ready and review |
| [#16](https://github.com/cmu-universal-agent/universal-agent-benchmark/pull/16) | Presentation-safe WS3 demo evidence | Draft and mergeable; no reviews or checks | Review privacy regression and meeting output, then mark ready |

Do not hard-code a future PR head in a commit on that same branch. Re-check
GitHub after every push.

## Workstream status

| Workstream | Current state |
|---|---|
| WS1 — scope and task selection | Complete: healthcare and e-commerce, three frameworks, and H1/H2/H4/H5/E1/E2/E3/E5 |
| WS2 — infrastructure and dataset preparation | Complete and merged; owner reviews for H2, H4, H5, and E3 are closed |
| WS3 — shared retail evaluation | Partially complete; contract, shared core, demo, dashboard prototype, and one real wrapper are present |
| WS4 — formal experiments | Not started; current outputs are engineering validation only |
| WS5 — analysis and final report | Not started as a formal workstream |

### WS3 completed on `main`

- Canonical tau-retail contract v0.2.0 with 16 tools, unified reset, state,
  error, trace, and final-state schemas.
- Deterministic shared `RetailEnv` core with 38 passing tests reported in the
  post-merge audit.
- A real LangGraph thin wrapper and one wrapper-evidence stream.
- Approved E5 v0.3 evaluator policy and public-safe replay tooling.
- Canonical LangGraph invalid-argument trace parity.
- Synthetic offline demo harness at `scripts/demo_ws3_offline.py`.
- Static dashboard prototype and result generator.
- Contract, adapter, shared-tool, leakage, reset, mutation, duplicate-action,
  and failure fixtures.

`wrapper_evidence=1` means one real framework wrapper, not three-framework
parity. Core-generated evidence must never be presented as framework evidence.

### WS3 still required

- Review/merge PR #16 so shareable demo files contain aggregates only.
- Implement a CrewAI WS3 retail wrapper and evidence.
- Implement an OpenAI Agents SDK WS3 retail wrapper and evidence.
- Correct the dashboard experiment-label collision and stale prototype tool
  semantics identified by PR #13.
- Add a concise methodology and limitations record.
- Run identical offline parity evidence across all three real wrappers.

WS3 is not complete until all three real wrappers produce schema-valid evidence
against the same shared core. A wrapper skeleton, core simulation, dashboard,
or synthetic demo does not satisfy that gate.

## E5 decisions and replay

Chloe approved the four owner-reviewed E5 case/gold records and the v0.3
response/final-state and run-policy semantics. `main` contains only the
public-safe evaluator, converter, synthetic controls, approval record, and
replay-fill code.

The private formal replay completed on 2026-07-29:

- four approved cases replayed cleanly;
- the source and retail snapshot were pinned and verified;
- source task/action identity and schemas were checked;
- any action exception is a hard failure;
- output is written atomically only after every case validates;
- a second independent run produced byte-identical output;
- the upstream retail environment has no user-side DB, so its canonical user
  DB hash is `null` by design.

The following remain local and must not be committed, attached to PRs, pasted
into issues, or used in an agent prompt:

- raw E5 cases and gold actions;
- evaluator-only response/final-state contracts;
- source snapshots and snapshot contents;
- initial/expected hashes;
- replayed evaluator output and raw traces;
- dedicated replay environment.

Current local-only replay locations:

- `C:\Users\Jessica\Documents\Universal Agent\tmp\e5-approved-20260729`
- `C:\Users\Jessica\Documents\Universal Agent\tmp\tau2-bench-replay-1d244f5`
- `C:\Users\Jessica\Documents\Universal Agent\tmp\.venv-e5-replay`

## Ownership and next actions

| Area | Owner | Reviewer | Next action |
|---|---|---|---|
| Canonical contract and cross-framework integration | Jessica | Relevant framework/data owner | Preserve owner-approved semantics while completing wrapper parity |
| E5 semantics and gold | Chloe | Jessica for integration/privacy | Approval complete; review only if public evaluator semantics change |
| Shared retail core | Xiaoxia | Jessica | Support wrapper integration and contract regressions |
| CrewAI WS3 wrapper | Mickey | Jessica/Xiaoxia | Implement real thin wrapper and common evidence |
| OpenAI Agents SDK WS3 wrapper | Lanfang | Jessica/Xiaoxia | Implement real thin wrapper and common evidence |
| Dashboard corrections | Xiaoxia | Jessica | Fix audit findings without claiming benchmark scores |
| Methodology and limitations | Mickey | Team | Document protocol, exclusions, and non-scoring limitations |
| LangGraph contract parity | Jessica | Chloe/framework reviewer | Complete and merged via PR #15 |

Jessica may implement infrastructure, approved deterministic conversion,
privacy checks, schemas, validators, replay plumbing, and cross-framework
integration. Jessica must not invent or revise another owner's gold semantics,
framework commitments, stress taxonomy, or publishable benchmark conclusions.

## Demo boundary

The meeting demo is a synthetic technical validation:

1. run the single-command offline harness;
2. show the 16-tool contract and deterministic reset;
3. show read, mutation, invalid-argument, disallowed-action, duplicate-action,
   tool-failure, and leakage controls;
4. inspect the public aggregate evidence and explain that full trace/final-state
   validation happens in memory;
5. state clearly that only LangGraph currently supplies real wrapper evidence.

Do not expose evaluator-only gold or present the demo as a benchmark score,
framework ranking, live E5 run, or three-wrapper parity result.

## Clean execution policy

Before a formal replay, smoke, or experiment:

1. verify the canonical checkout is clean and tracks latest `official/main`;
2. create a fresh worktree for the exact PR or experiment commit;
3. create a fresh virtual environment from that commit's pinned requirements;
4. record commit, dependency source, experiment ID, and non-scoring/scoring
   label;
5. run deterministic offline checks before any authorized model call;
6. keep raw outputs and evaluator-only data outside Git.

Do not reuse an old branch or virtual environment merely because it still
runs. Preserve active PR worktrees; remove merged/superseded worktrees only
after mapping them to GitHub and checking for unique local commits.

## Validation

Use a fresh environment appropriate to the framework. Core checks do not
require live model calls:

```powershell
python .\scripts\validate_contract_fixtures.py
python .\scripts\validate_adapter_contracts.py
python .\scripts\validate_shared_tool_contracts.py
python .\scripts\validate_ws3_tau_retail_contract.py
python -m unittest discover -s .\tests\retail_core -p "test_*.py"
python .\scripts\demo_ws3_offline.py
```

For E5 changes, also run conversion, run-policy, synthetic-smoke, leakage, and
pinned replay tests. Never run live model calls merely to refresh status.

## Publishing rules

Before publishing:

1. inspect the exact diff and stage named files only;
2. run checks proportional to the change;
3. push to `official`, not the personal `origin`;
4. verify the resulting PR head, base, mergeability, reviews, and checks;
5. keep all preliminary results labelled “not benchmark scores.”

Never publish `.env`, credentials, virtual environments, raw dataset caches,
evaluator-only gold, snapshots, hashes, replay outputs, raw traces, or generated
metrics without explicit approval.

## Session handoff

Use:

```text
Outcome:
Evidence/commit/PR:
Confirmed decisions:
Completed work:
Open owner decisions:
Unassigned work:
Safe next actions for Jessica:
Tests run and results:
Files intentionally kept local:
```

Update this guide only for verified changes in repository state, ownership,
gates, validated evidence, or privacy boundaries. Do not paste transcripts or
duplicate detailed schema documentation.
