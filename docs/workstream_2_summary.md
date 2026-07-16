# Workstream 2 Summary

Last updated: July 16, 2026

## Status

Jessica's Workstream 2 work that can be completed without making dataset or
scoring decisions for other owners is complete. The overall team workstream is
not yet closed: dataset-specific mappings, eight formal converted tasks, and
the controlled pilot still depend on inputs and review from other owners.

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
- Approve the received H2 HealthBench draft after reviewing its provisional
  difficulty thresholds and the urgent/routine/self-care keyword subclassifier;
  then review the first converted samples. HealthBench has no native split, so
  engineering will generate a deterministic locked benchmark split.
- Approve the received H4 ACI-Bench extraction and difficulty rules for
  symptoms, history, risks, and next steps, then review generated samples.
- Provide initial H5 clarify/escalate examples and their rubric.
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

After Chloe's approved templates arrive, Jessica will implement deterministic
converters/extractors, generate review samples, run coverage/schema/leakage and
split-manifest validation, then execute the eight-task controlled comparison
after the framework entry points are ready.
