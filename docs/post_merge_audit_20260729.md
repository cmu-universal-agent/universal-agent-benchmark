# WS3 integration audit refresh - 2026-07-29

Verified baseline: official `main` at
`07d87a8567ec5f7d9c3826599773f8568a1142e8` after PRs #14 and #15 merged.

This is a public-safe status audit. It contains no E5 evaluator-only cases,
gold, snapshots, hashes, traces, outputs, or benchmark scores.

## Outcome

The original audit's two Jessica-owned P1 defects are resolved:

- PR #15 routes LangGraph missing and unexpected arguments through
  `RetailEnv`, preserving canonical rejected traces.
- PR #14 integrates the approved E5 v0.3 evaluator, local-batch converter,
  pinned replay fill, synthetic controls, retry/sweep policy, and native
  `tau3_db` sanity record.
- The private E5 gold replay completed 4/4 clean and remains outside Git.
- `verticals/retail/cases/RETAIL-E5-001.json` is explicitly a public
  `synthetic_fixture`, not a formal E5 case.

WS3 is still incomplete because only LangGraph has a real retail wrapper.
CrewAI and OpenAI Agents SDK wrappers, common three-wrapper evidence,
methodology/limitations, and final experiment configuration remain open.

## Resolved findings

### LangGraph invalid-argument parity

Resolved by PR #15, merged as `8d567947a37ce48586af280ce801630b58ee627b`.
The real wrapper path now reaches the shared core and has wrapper-level
regression coverage.

### Public-safe E5 integration

Resolved by PR #14, merged as `07d87a8567ec5f7d9c3826599773f8568a1142e8`.
`main` now contains:

- `adapter/e5_evaluator.py`;
- `adapter/e5_run_policy.py`;
- `scripts/run_e5_smoke.py`;
- `scripts/fill_e5_replay.py`;
- `docs/e5_gold_semantics_v0.3.md`;
- conversion from the gitignored owner-reviewed batch.

The verdict is `pass` only when Criterion A and Criterion B both hold and no
failure class is detected. A harness error is retried once; a final error rate
above 5 percent invalidates that framework sweep.

## Open findings

### P1 — Two real WS3 retail wrappers are missing

Current `main` contains a real LangGraph retail wrapper and evidence builder.
It does not contain equivalent `RetailEnv` wrappers/evidence for:

- CrewAI;
- OpenAI Agents SDK.

Required action: each framework owner adds a thin wrapper over the existing
shared core and emits the same schema-valid offline evidence.

Owners:

- CrewAI: Mickey;
- OpenAI Agents SDK: Lanfang;
- parity/integration review: Jessica and Xiaoxia.

### P1 — Three-wrapper parity evidence is missing

`wrapper_evidence=1` is one real framework, not cross-framework parity.
Synthetic core evidence must not be relabelled as framework evidence.

Required action: run identical reset, read, mutation, invalid-argument,
disallowed-tool, duplicate-action, failure-recovery, and leakage scenarios
through all three real wrappers.

### P2 — Demo evidence hardening is still Draft

PR #16 keeps full synthetic evidence in memory for validation while writing
only presentation-safe aggregates to JSON/HTML. It is still Draft.

Required action: review and merge PR #16 before sharing generated meeting
artifacts. The demo remains synthetic technical validation, not a formal E5
run or framework ranking.

### P2 — Dashboard corrections remain open

The dashboard still needs:

- `experiment_label` included consistently in generated JavaScript lookup
  keys, so rows from different experiments do not overwrite each other;
- the static prototype checked against the canonical non-mutating
  `transfer_to_human_agents(summary=...)` contract.

Owner: Xiaoxia. Reviewer: Jessica.

### P2 — Methodology, limitations, and automated gates are missing

There is still no concise WS3 methodology/limitations artifact and no
repository CI workflow that proves the portable offline gate.

Required action:

- Mickey records protocol, exclusions, rerun policy, and non-scoring
  limitations;
- the team adds one environment-aware offline command and a minimal CI matrix
  before formal experiments.

### P3 — Status documentation needs one more refresh

This PR updates the README's merged/open PR and WS3/E5 status. The
`docs/PROJECT_LEAD_GUIDE.md` copy on `main` still predates the merges of PRs #14
and #15 and should be refreshed from latest `main`, not from this audit's older
base.

## Validation evidence

Merged validation recorded by PRs #14 and #15:

```text
E5 run-policy, converter, and leakage tests: 10 passed
Shared retail core: 38 passed
E5 synthetic smoke: 11/11 controls
Contract fixtures: 14 valid, 11 expected-invalid, 5 schemas
LangGraph invalid-argument wrapper regression: passed
```

No live model calls or formal benchmark runs were made for this audit refresh.

## Recommended sequence

1. Add the CrewAI and OpenAI Agents SDK retail wrappers.
2. Produce identical offline evidence from all three real wrappers.
3. Review and merge PR #16 for presentation-safe demo artifacts.
4. Fix the dashboard lookup/prototype issues.
5. Add methodology/limitations and the portable offline CI gate.
6. Freeze model, simulator, seed, budget, and run manifest.
7. Only then start formal E5 three-framework experiments.
