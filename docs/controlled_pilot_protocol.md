# Controlled Pilot Execution Protocol

Status: **Historical v1.6 baseline; superseded for formal execution by v2.0**
Owner: Mickey
Prepared: 2026-08-15; integration status refreshed 2026-08-17
Pilot protocol: `pilot-60-v1.6` historical baseline
E5 session protocol: `1.6` historical baseline

## Purpose and claim status

This document governs Workstream 4 execution of the controlled 60-case pilot.
It freezes the run arithmetic, readiness gates, execution order, retry rules,
run identity, and privacy boundary. Analysis, framework comparisons, report
chapter ownership, and final-deliverable terminology are Workstream 5 and are
outside this protocol.

Runs governed by this v1.x protocol remain immutable `technical_smoke_only`
evidence. Formal v2.0 execution is governed by
`docs/formal_benchmark_protocol_v2.0.md` and does not relabel or reuse them.

## Historical candidate baseline

| Item | Candidate evidence | Freeze rule |
|---|---|---|
| Representative-case documentation | PR #25 merged as `9a2248c` | IDs and owner semantics must remain unchanged |
| Preflight hardening | PR #26 merged as `8b8e5bb` on 2026-08-16 | Preserve the merged `main` commit |
| E5 v1.6, run/attempt linkage, and exact-repeat selection | PR #27 merged as `464a0d5` on 2026-08-17 | Preserve the merged `main` commit |
| Formal code commit | Integrated code baseline `464a0d5`; no v1.x formal freeze | Formal execution moved to v2.0 |

The merged PR #27 commit was integration evidence, not a formal execution
commit. Formal execution later began under the independently frozen v2.0
protocol and commit.

## Execution terms

These definitions are limited to WS4 execution:

- **Case:** one frozen benchmark record identified by `case_id` and `task_id`.
- **Logical run:** one planned observation of one case on one framework under
  one `experiment_id` and repeat number.
- **Attempt:** one execution try for a logical run. Every logical run starts at
  attempt `1`; attempt `2` is only an eligible infrastructure retry.
- **Readiness preflight:** a technical gate run used to verify the frozen
  environment and result path. It is not a controlled-pilot result row.
- **Main-pilot run:** the first controlled observation for a case/framework
  pair.
- **Targeted repeat:** the second or third controlled observation for one of
  the eight frozen representative cases.
- **Run ID:** the unique ID written by a framework result. It is distinct from
  the runner's logical-run ID.

Retry attempts never create new logical runs and never increase the planned
run counts.

## Frozen scope and configuration

| Item | Required value |
|---|---|
| Tasks | `H1`, `H2`, `H4`, `H5`, `E1`, `E2`, `E3`, `E5` |
| Cases | 60: eight each for H1/H2/H4/H5/E1/E2/E3 and four for E5 |
| Frameworks | OpenAI Agents SDK, LangGraph, CrewAI |
| Agent model | `gpt-4o-mini` through the frozen OpenAI-compatible provider |
| E5 user-simulator model | `gpt-4o-mini` |
| Temperature | `0` |
| Maximum output tokens | Pending final freeze: record one explicit requested value; if unsupported, record `null`/`unsupported` and the exact provider/model version instead of relying on a provider default |
| Seed | Record the requested and effective value; use null when the provider does not support it |
| Per-attempt timeout | 300 seconds |
| Token budget | No separate cap; record provider-reported usage when available |
| Python | 3.12.13 in the frozen execution environment |
| Framework packages | `openai-agents==0.18.0`, `langgraph==1.2.8`, `crewai==1.15.1` |
| Manifest | Private `pilot-60-v1.0`, 60/60 owner-approved cases, with SHA-256 in the private freeze record |
| Evaluators | H1/H2/H4/H5/E1/E2/E3 semantics 1.0; E5 semantics 0.3; hashes retained privately |
| Results | Private local-only JSONL and append-only attempt ledger |

Before any preflight call, a candidate freeze record must capture the exact
merged `main` commit, configuration, and preflight experiment ID. After all 24
preflights pass, the final freeze record must capture the formal experiment ID,
dependency lock evidence, provider endpoint identity, prompt and schema
versions, output root, timestamps, approver, and successful readiness checks.
The formal code and configuration must match the preflight candidate; otherwise
version the change and repeat the affected preflights. Do not reconstruct any
of these values after execution.

## Readiness gates

Complete the gates in this order:

1. **Code gate:** PR #26 and PR #27 are integrated into `main`; the checkout is
   clean and pinned to the recorded formal commit.
2. **Data gate:** the private manifest contains 60 unique cases, evaluator-only
   gold contains 60 linked approved records, the eight representative IDs
   match this document, hashes match the private freeze record, and leakage
   validation reports zero findings.
3. **Environment gate:** use fresh dedicated Python 3.12 environments from the
   frozen commit; `pip check`, shared offline checks, and all three wrapper
   suites pass. The wrapper-evidence validator must report
   `wrapper_evidence=3`.
4. **Discovery gate:** `run_benchmark.py --list-only` resolves exactly the
   intended cases with no duplicate identity, model calls, or result writes.
5. **Repeat-selection gate:** the runner can execute or retry one exact
   `(experiment_id, case_id, framework, repeat)` without executing an earlier
   successful repeat. Merged PR #27 commit `464a0d5` provides `--repeat N`;
   this gate passes after validation on the frozen candidate commit.
6. **Preflight gate:** run one case for each of the eight tasks on each of the
   three frameworks, for 24 logical runs under the candidate commit,
   configuration, and preflight experiment ID frozen before the first call.
   Each must finish with exactly one linked, schema-valid, traceable final
   result and no privacy violation; preserve any eligible failed attempt.
7. **Freeze gate:** record the exact formal configuration and approvals after
   all 24 preflights pass. Start the controlled pilot only after this record is
   complete.

A preflight's task score is diagnostic evidence, not a reason to retry. A poor
answer may expose a real model limitation; only a technical defect in the
protocol, environment, runner, adapter, evaluator handoff, or result write can
fail readiness. Any post-freeze code, data, evaluator, prompt, or configuration
change requires a new protocol version and repeated affected preflights.

## Run matrix

### Phase totals

| Phase | Calculation | Logical runs | Controlled-pilot results? |
|---|---:|---:|---|
| Readiness preflight | 8 tasks x 3 frameworks x 1 | 24 | No |
| Main pilot | 60 cases x 3 frameworks x 1 | 180 | Yes |
| Additional targeted repeats | 8 cases x 3 frameworks x 2 | 48 | Yes |
| Controlled-pilot total | 180 + 48 | 228 | Yes |
| Full WS4 execution plan | 24 + 228 | 252 | Mixed |

### Task-level matrix

| Task | Frozen cases | Preflights | Main runs | Representative case | Additional repeats | Controlled total |
|---|---:|---:|---:|---|---:|---:|
| H1 | 8 | 3 | 24 | `H1-REVIEW-001` | 6 | 30 |
| H2 | 8 | 3 | 24 | `H2-REVIEW-001` | 6 | 30 |
| H4 | 8 | 3 | 24 | `H4-REVIEW-001` | 6 | 30 |
| H5 | 8 | 3 | 24 | `H5-REVIEW-001` | 6 | 30 |
| E1 | 8 | 3 | 24 | `E1-REVIEW-001` | 6 | 30 |
| E2 | 8 | 3 | 24 | `E2-REVIEW-001` | 6 | 30 |
| E3 | 8 | 3 | 24 | `E3-REVIEW-001` | 6 | 30 |
| E5 | 4 | 3 | 12 | `E5-001` | 6 | 18 |
| **Total** | **60** | **24** | **180** | **8 IDs** | **48** | **228** |

Each framework contributes 60 main runs and 16 additional targeted repeats,
for 76 controlled-pilot results. Its eight preflights bring its full WS4 plan
to 84 logical runs.

### Representative-case schedule

For every representative ID above and every framework:

| Repeat | Role | Planned attempts |
|---:|---|---|
| 1 | Main-pilot observation | Attempt 1; attempt 2 only for eligible infrastructure failure |
| 2 | First additional targeted repeat | Same rule |
| 3 | Second additional targeted repeat | Same rule |

The public synthetic fixture `RETAIL-E5-001` is not the formal E5 case
`E5-001` and must never enter this matrix.

## Execution order

1. Run the 24 preflights under a preflight-only experiment ID. Preserve every
   attempt but exclude these runs from controlled-pilot aggregates.
2. Freeze a new formal experiment ID after the preflight gate passes.
3. Execute the 52 non-representative cases once on each framework.
4. Execute the eight representative cases three times on each framework.
   Repeat 1 supplies their main-pilot observation; repeats 2 and 3 supply the
   48 additional targeted-repeat observations.
5. Authorize attempt 2 only after a human reviewer confirms attempt 1 was an
   eligible infrastructure failure. Do not retry a low score, wrong answer,
   unsafe answer, formatting failure attributable to the model, or poor tool
   choice.
6. Stop the affected execution when run identity, configuration, data hashes,
   privacy, or result linkage differs from the frozen record.

Use private execution views for the 52 non-representative cases and the eight
representative cases. Each view must preserve the original case bytes and the
correct sibling evaluator-only gold layout. Record the view manifests and
hashes locally; do not commit them.

## Run identity and attempt ledger

The merged v1.6 runner constructs logical-run IDs as:

```text
<experiment_id>:<case_id>:<framework>:repeat-<repeat>
```

Every result must record `logical_run_id`, `repeat`, `attempt`, and `run_id`.
The append-only attempt ledger must record the same logical identity plus the
matching `result_run_id`, result-row count, status, timeout, timestamps, return
code, and rerun reason.

For a completed attempt, exactly one result row and one non-empty `run_id` must
join to the ledger entry. Preserve all attempts. Aggregate analysis may use the
latest eligible attempt for a logical run, but may not delete or overwrite the
original. More than 5 percent final-attempt errors invalidate the affected
framework sweep under the frozen E5 policy.

## Rerun policy

Attempt `2` requires all of the following:

1. attempt `1` is retained unchanged;
2. a human reviewer classifies the failure as infrastructure;
3. the exact logical run is selected without touching another logical run;
4. the ledger records a specific non-empty reason; and
5. the same frozen code, case, framework, model, and configuration are used.

No third attempt is permitted. If the retry would require a code, dependency,
prompt, case, gold, evaluator, or configuration change, create a new protocol
version and repeat the affected readiness gates instead.

## Repeat-selection implementation status

Merged PR #27 commit `464a0d5` adds a mutually exclusive `--repeat N` path so
repeat 2 or 3 can be executed or retried without revisiting repeat 1. Shared
suites pass 104/104 in all three pinned Python 3.12 environments and wrapper
suites pass 7/7, 8/8, and 8/8. A non-empty `--rerun-reason` still does not prove
that the selected prior attempt was an eligible infrastructure failure; the
human eligibility review remains required.

Do not start the formal 228-run pilot until the exact final merged `main` is
frozen and the repeat-selection gate passes on that commit. Do not edit the
append-only ledger to work around this gate.

## Privacy and publication boundary

Keep all of the following outside Git and public artifacts:

- evaluator-only gold, H5 criterion annotations, and E5 response/final-state
  contracts;
- private cases or source snapshots that are not approved for publication;
- manifest, dataset, gold, replay-state, and result hashes;
- provider credentials and private endpoint details;
- raw outputs, attempt ledgers, raw traces, replay output, and detailed result
  rows; and
- private execution-view manifests and paths.

Agent runs may receive only agent-visible case content and allowed tool results.
For E5, only the approved user-simulator fields may cross the provider boundary.
The public dashboard remains aggregate-only and allowlisted.

## WS4 completion record

Mickey's written-protocol and representative-run-matrix tasks are complete when
the team accepts this document. Formal execution remains blocked until the
code, repeat-selection, preflight, and freeze gates pass. Those gates do not
convert this protocol into a WS5 report or authorize benchmark claims.
