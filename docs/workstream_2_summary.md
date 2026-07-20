# Workstream 2 Summary

Last updated: July 20, 2026

## Status

Jessica's Workstream 2 infrastructure and the H2/H4 revisions requested by
Chloe are implemented and pass offline validation. Jessica selected the
handoff-with-carry-overs closure path on July 20, 2026, so WS3 planning may
start. H2 urgency review is complete, its provisional difficulty rule is
retained for later calibration, and the E3 pending-order ambiguity is resolved.
H4 sample re-review and four H5 rubric second passes remain Chloe-owned
carry-overs; they block final semantic freeze, not WS3 contract work.

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
- Re-review the regenerated H4 sample after the v2 fixes for boilerplate,
  abbreviated headers, newline splitting, missing HPI history, and semantic
  problem-title routing; then approve or revise the extraction/difficulty rules.
- Perform the stated second-pass review on the four supplied H5 cases and
  rubrics (two `clarify`, two `escalate`). Their exact evaluator content remains
  local and gitignored until approval.
- Treat the E3 `cancel_pending_order` decision as closed: all such scenarios
  are excluded from E3 and are never mapped to `refund_allowed`.
- Review 5–10 generated samples per task; no bulk manual labeling is required.

### Mickey

- Finish and review CrewAI integration ownership, including Windows/Linux
  requirements and unified task/result compatibility.
- Verify allowed-tools behavior and no-tool/success/failure paths.
- Document supported and unavailable CrewAI result fields.
- Prepare CrewAI's eight-task test entry after formal cases are ready.
- Coordinate shared adapter/schema/runner changes before integration and
  confirm the first controlled pilot size.

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

- Review and merge this Workstream 2 pull request.
- Grant or confirm contributor access to the official
  `cmu-universal-agent/universal-agent-benchmark` repository before the next
  upstream synchronization.

## Jessica's Next Actions After Handoff

Start WS3 in a separate branch only after confirming its relationship to Draft
PR #1. First assign the shared simulator/core owner and reviewer, assign all
three wrapper owners, and approve the canonical tool/state contract. Apply any
later H4/H5 owner corrections as isolated carry-over changes and rerun the
offline gate. The eight-task controlled comparison starts only after remaining
task semantics and framework entry points are ready.
