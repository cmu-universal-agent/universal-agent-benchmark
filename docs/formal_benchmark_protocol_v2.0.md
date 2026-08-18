# Formal Controlled-Pilot Benchmark Protocol v2.0

Status: **Revision r3 candidate freeze; no r3 provider call has started**

Execution owner: Jessica

Prepared: 2026-08-17

Protocol ID: `pilot-60-v2.0`

Implementation freeze revision: `r3`. The earlier `da35b7d` candidate stopped
after exposing an H5 summary-only null-score defect. The subsequent `d0affc8`
r2 candidate exposed a missing local E5 gold-path binding after 21 valid
non-E5 results and three traceable E5 infrastructure failures. All candidate
rows remain immutable engineering evidence and are excluded from the fresh r3
readiness gate, analysis, claims, and denominators.

## Purpose

This protocol starts a new, prospective formal controlled-pilot benchmark after
the earlier readiness schedule was missed. It imports the scope, evaluator
semantics, run arithmetic, retry policy, run identity, and privacy boundary from
`docs/controlled_pilot_protocol.md` without relabeling or reusing any v1.x run.

The v1.0-v1.6 attempts remain immutable `technical_smoke_only` evidence. They
may inform engineering checks and limitations, but they are excluded from the
v2.0 readiness gate, result aggregates, repeats, claims, and denominators.

## Candidate code baseline

- GitHub `main` after PR #28: `56838d4c1f4743f61c457fee6fe2609fa52fed57`.
- The final v2.0 execution commit is the merged commit containing this file.
- No provider call may start until that exact commit passes every zero-call
  gate and is recorded in the private freeze record.
- Any later code or configuration change creates a new protocol version and
  repeats every affected preflight.

## Frozen scope

| Item | v2.0 value |
|---|---|
| Tasks | H1, H2, H4, H5, E1, E2, E3, E5 |
| Cases | 60: eight per non-E5 task and four E5 cases |
| Frameworks | OpenAI Agents SDK, LangGraph, CrewAI |
| Agent model | `gpt-4o-mini` |
| E5 user simulator | `gpt-4o-mini` |
| Agent generation settings | temperature `0`; requested maximum output tokens `4096`; requested seed `42` |
| E5 simulator generation settings | temperature `0`; maximum output tokens `4096`; scenario seed from the frozen evaluator-only gold |
| Per-attempt timeout | 300 seconds |
| Framework environments | Three isolated Python 3.12 environments from committed requirement files |
| Manifest | Private frozen `pilot-60-v1.0`, unchanged |
| Evaluators | H1/H2/H4/H5/E1/E2/E3 semantics 1.0; E5 semantics 0.3, unchanged |
| Output | Private local-only JSONL, attempt ledger, evaluator records, and freeze evidence |
| Retry | Attempt 2 only for a documented infrastructure failure; no third attempt |

Model aliases, provider endpoint identity, package versions, manifest/evaluator
hashes, local paths, and the cost ceiling are captured in the private freeze
record rather than this public document.

## Prospective readiness gate

The v2.0 preflight uses one frozen representative case for each task on each
framework, producing 24 new logical runs under a preflight-only experiment ID.
No v1.x attempt counts toward this gate.

The gate passes only when:

1. the checkout is clean at the exact v2.0 commit;
2. all private manifest, gold, approval, and evaluator hashes match;
3. all three Python environments pass `pip check`, shared suites, framework
   wrapper suites, and `wrapper_evidence=3`;
4. list-only discovery resolves the intended frozen cases with no model call
   or result write;
5. every preflight logical run has one joined final result row, valid identity,
   schema/trace/evaluator disposition, and no privacy violation; and
6. every eligible retry preserves attempt 1 and uses the same frozen code,
   model, case, framework, and configuration.

A normally completed model/evaluator `fail` is a valid frozen preflight outcome
and is never retried for score. It does not fail infrastructure readiness when
the output is captured, classified, and traceable. A final infrastructure
error, missing/duplicate result row, privacy violation, configuration drift, or
unclassified evaluator state fails the gate.

## Formal execution matrix

After the readiness gate passes, freeze a separate formal experiment ID and
execute exactly:

| Phase | Logical runs | Included in benchmark results |
|---|---:|---|
| Fresh v2.0 preflights | 24 | No |
| Main pilot | 180 | Yes |
| Additional targeted repeats | 48 | Yes |
| Formal controlled-pilot results | 228 | Yes |
| Total v2.0 execution plan | 252 | Mixed |

The eight representative IDs remain exactly those in
`docs/representative_case_ids.md`. Repeat 1 is their main-pilot observation;
repeats 2 and 3 are the additional observations. Retry attempts do not add
logical runs.

## Privacy and cost gate

Agent runs receive only frozen agent-visible prompts and allowed tool results.
For E5, the agent-visible prompt and conversation may be sent to the agent
model; only the approved structured `user_simulator.task_instructions`
rendering may be sent to the `gpt-4o-mini` user simulator. Response contracts,
gold actions, rubrics, expected state, hashes, replay output, and raw evaluator
records remain local.

Before the first provider call, the private authorization record must name the
exact execution commit, preflight experiment ID, models, outbound allowlist,
maximum spend, authorizer, and timestamp. Stop before the ceiling is exceeded.

## Claim boundary

When every gate passes, v2.0 may be reported as a **formal controlled-pilot
benchmark within this frozen 60-case scope**. It does not establish production
robustness, statistical superiority, a composite score, or an overall best
framework. Partial or gate-failed execution must be labeled incomplete and may
not be promoted to a formal result set.
