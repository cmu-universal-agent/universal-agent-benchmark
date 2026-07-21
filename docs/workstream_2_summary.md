# Workstream 2 Summary

Last updated: July 21, 2026

## Status

Jessica's Workstream 2 infrastructure and the H4 v3 revisions requested by
Chloe are implemented and pass offline validation. H2 urgency review is
complete, its provisional difficulty rule is retained for later calibration,
and the E3 pending-order ambiguity is resolved. Chloe approved all four H5
cases/rubrics on July 21. H4 v3 is the only remaining WS2 semantic-review gate.
Jessica explicitly directed that PR #1 and stacked CrewAI PR #2 must not be
merged until H4 owner review and final validation are complete.

## Completed by Jessica

- Reconciled the current repository with the five Benchmark Case, healthcare,
  e-commerce, tool-call, and run-log schemas.
- Incorporated Chloe's schema feedback and recorded the field design as frozen
  for pilot implementation, with formal v1.0 release gated by integration.
- Added valid/invalid schema fixtures and framework-neutral validation for
  legacy/v1 compatibility, aggregate source limits, evaluator-data isolation,
  deterministic split manifests, mapping coverage, tool-result truncation,
  and normalized tool paths.
- Verified no-tool, tool-success, and tool-failure contracts.
- Added strict machine-readable smoke checks, fixing a false 100% instruction
  score when an exact literal constraint was missed.
- Added token-usage collection to OpenAI Agents SDK, LangGraph, and CrewAI.
- Ran the same clean live smoke task across all three adapters. The run proved
  API/runtime connectivity, JSON output, metadata recording, and strict
  evaluation; it is not a framework-performance conclusion.
- Kept credentials, virtual environments, dataset caches, traces, and generated
  JSONL metrics out of version control.

## Remaining Owner Inputs

### Chloe

- Return the remaining dataset/version, source ID/gold fields, transformation,
  missing/ambiguous/unmapped handling, and audit templates.
- H2 urgency review is complete: H2-003 is `urgent`, H2-004 and H2-005 are
  `routine`, and H2-008 is `self_care`. No further Chloe action is required for
  H2. The current difficulty distribution (easy=90, medium=10, hard=353) is
  explicitly provisional and retained for now as a later engineering task.
- Review the regenerated H4 v3 eight-case pack after fixes for secondary
  history-title leakage, `Dr.`/`Mr.`/`Ms.` sentence splitting, short same-line
  `Denies ...` statements, and infection/lingering-cold HPI coverage; then
  approve or revise the extraction/difficulty rules.
- Treat H5 as closed: all four supplied cases and rubrics (two `clarify`, two
  `escalate`) were approved on July 21. Exact evaluator content remains local
  and gitignored.
- Treat the E3 `cancel_pending_order` decision as closed: all such scenarios
  are excluded from E3 and are never mapped to `refund_allowed`.
- Review the eight regenerated H4 samples; no bulk manual labeling is required.

### Mickey

- CrewAI integration is implemented in stacked PR #2, including legacy/v1
  task/result compatibility, `allowed_tools` cases, no-tool/success/failure
  contracts, result checking, Windows import hardening, and telemetry defaults.
- The PR records an offline 46/46 test pass, schema-fixture checks, Windows
  dependency consistency, Linux dependency resolution, and eight list-only
  task entries. These are technical checks, not benchmark results.
- Remaining external gates are live-model smoke with local API configuration,
  native Linux/CI confirmation, formal generated cases/gold, and E5 integration
  with the shared tau-retail simulator/tool registry.
- Keep PR #2 separate and stacked; do not merge or retarget it until the PR
  integration sequence is approved.

### Xiaoxia / Dashboard Owner

- Continue dashboard field mapping and views using the frozen pilot field
  design.
- Treat synthetic/mock values as fixtures, not benchmark results.
- Account for nullable/partial fields such as pricing, repair metadata, and
  output-schema validation until their integration gates are complete.

### Lanfang / Stress-Test Owner

- Confirm the first stress scenarios, expected failure classifications, tool
  requirements, repeated-run design, long-context cases, and conflicting
  evidence cases.

### Repository / Integration Owner

- Review the Workstream 2 PRs, but do not merge while the current hold is active.
- Grant or confirm contributor access to the official
  `cmu-universal-agent/universal-agent-benchmark` repository before the next
  upstream synchronization.

## Jessica's Next Actions After Handoff

Continue WS3 planning, but start implementation in a separate branch only after
confirming its relationship to Draft PR #1 and stacked PR #2. First assign the
shared simulator/core owner and reviewer, assign all three wrapper owners, and
approve the canonical tool/state contract. Apply any H4 owner corrections and
rerun the complete offline gate before merge. The eight-task controlled
comparison starts only after remaining task semantics and framework entry
points are ready.
