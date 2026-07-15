# Workstream #2: Current Status and Asynchronous Handoff

Last updated: July 15, 2026

## Purpose

This document lets the team continue asynchronously across time zones. It
separates completed infrastructure work, work that can continue now, and work
blocked by the pending schema field review.

## Current Snapshot

The project has a functional multi-framework base for LangGraph, CrewAI, and
the OpenAI Agents SDK. Framework dependencies are isolated, shared runtime
metadata and normalized tool traces are partially implemented, and legacy task
files remain runnable.

The five JSON Schema files are valid Draft 2020-12 schemas, but they are still
drafts until Chloe completes the scoring and dashboard field review. The
current runtime result envelope records many of the proposed fields, but it is
not yet a complete schema-valid implementation of `run_log.schema.json`.

There are currently no model-generated JSONL benchmark results in the
repository. No comparative framework conclusion should be drawn yet.

## Completed

- Created isolated environments and wrappers for:
  - OpenAI Agents SDK 0.18.0
  - LangGraph 1.2.8
  - CrewAI 1.15.1
- Added Windows-compatible setup and smoke-test scripts.
- Added draft schemas for benchmark cases, healthcare output, e-commerce
  output, tool calls, and run logs.
- Added common run metadata, including run and experiment IDs, framework and
  model metadata, timestamps, raw output, and normalized tool-call traces.
- Added model-controlled benchmark options (`--model`, `--experiment-id`, and
  `--repeats`).
- Added a shared loader that accepts both legacy task files and Benchmark Case
  Schema v1.0 files.
- Enforced the v1.0 `allowed_tools` list consistently across all three
  framework adapters.
- Added `scripts/validate_tasks.py` to distinguish valid v1.0, compatible
  legacy, and invalid task files.
- Added safe dataset preparation modes:
  - `--cache-only` downloads/reads caches without changing tasks.
  - Existing task files cannot be replaced without explicit `--overwrite`.
- Confirmed that all 21 current task files are legacy-compatible and invalid
  count is zero.

## Validation Completed

- 23 Python files passed syntax parsing.
- All five schema files passed JSON Schema definition checks.
- The Benchmark Case Schema v1.0 example passed formal validation.
- Legacy and v1.0 task loading passed.
- Tool filtering passed for all three frameworks.
- Dataset overwrite guards passed.
- `--require-v1` correctly blocks a formal run while legacy tasks remain.

## Current Blockers and Pending Decisions

### Waiting for Chloe

- Confirm which schema fields are required, optional, or nullable.
- Confirm which fields are needed for scoring and dashboard views.
- Confirm final task/vertical naming and enumerations.
- Confirm ground-truth and evaluator-rubric storage outside agent-visible case
  files.
- Confirm output-schema requirements for the first eight core tasks.
- Approve the schema as formal v1.0.

### After Chloe's Review

- Update the draft schemas based on approved decisions.
- Add a migration/conversion process for the 20 pilot tasks.
- Move ground truth to the approved evaluator-only structure.
- Update evaluator and reporting field mappings.
- Complete the runtime-to-`run_log.schema.json` serialization layer.
- Add valid and invalid schema fixtures.
- Configure local API credentials and dataset caches.
- Run one task across all three frameworks before expanding the test matrix.

## Xiaoxia: Work That Can Continue Now

Xiaoxia can work on the dashboard structure without waiting for final model
runs. Please treat all schema fields as provisional until sign-off.

Suggested tasks:

1. Create a dashboard field mapping based on:
   - `schemas/run_log.schema.json`
   - `schemas/tool_call.schema.json`
   - `docs/schema_field_review.md`
2. Propose filters for experiment, vertical, task, framework, model, stress
   type, status, and date/time.
3. Propose summary cards for run count, success rate, schema-valid rate,
   average latency, tool success/error rate, and token/cost coverage.
4. Propose comparison views for framework-by-model and vertical-by-stress-type.
5. Design a tool-call detail view showing sequence, allowed/rejected status,
   arguments validity, latency, outcome, and error type.
6. Use clearly labeled mock data for the wireframe; do not treat mock values as
   benchmark results.
7. Mark fields that the current adapters do not yet provide consistently. In
   particular, verify token usage, estimated cost, output repair, output schema
   validity, and structured error stages.
8. Return questions or requested field changes in
   `docs/schema_field_review.md` rather than changing schema meaning silently.

Suggested deliverables:

- `docs/dashboard_requirements.md`
- `docs/dashboard_field_mapping.md`
- A dashboard wireframe or component layout
- Optional mock run-log fixtures clearly stored as test/mock data

## Coordination Needed

### Lanfang Hai

- Review the proposed `stress_type` values.
- Define the first stress scenarios and expected failure classifications.
- Confirm which stress tests require tools, simulated tool failure, repeated
  runs, long context, or conflicting evidence.

### Mickey

- Confirm branch and pull-request ownership.
- Resolve cross-workstream decisions and approve the integration sequence.
- Confirm whether the first pilot uses all 20 existing cases or only the eight
  agreed core tests.

### Jessica

- Maintain framework adapters and the compatibility loader.
- Integrate Chloe's approved schema decisions.
- Run the first controlled three-framework comparison after configuration is
  complete.
- Verify that every framework records the same required fields.

## GitHub Handoff Recommendation

Do not upload a full downloaded folder over the repository. Do not commit
virtual environments, API credentials, dataset caches, or generated metrics.

Recommended workflow:

1. Clone the official repository into a new directory.
2. Create a branch such as `jessica/infrastructure-schema-compat`.
3. Copy only the changed source and documentation files from the working copy.
4. Run task validation and syntax checks.
5. Commit and push the branch.
6. Open a draft pull request titled:
   `[WIP] Infrastructure compatibility, schema validation, and async handoff`
7. In the pull request, state that schema sign-off, task migration, and live
   model tests are still pending.
8. Ask Xiaoxia to branch from this branch or coordinate changes through the
   same draft pull request to avoid duplicated field definitions.

Do not commit:

- `.env`
- `.venv-*`
- `data/`
- `results/metrics/`
- `results/traces/`
- Python cache files

## Useful Commands

Validate current tasks without calling a model:

```powershell
.\.venv-crewai\Scripts\python.exe scripts\validate_tasks.py
```

Download dataset caches without replacing tasks:

```powershell
.\.venv-openai\Scripts\python.exe scripts\prepare_medical_tasks.py --cache-only
.\.venv-openai\Scripts\python.exe scripts\prepare_ecommerce_tasks.py --cache-only
```

After formal migration, require every task to be v1.0:

```powershell
.\.venv-crewai\Scripts\python.exe scripts\validate_tasks.py --require-v1
```

## Definition of Ready for the First Controlled Run

- Schema field review approved.
- Eight core pilot tasks selected and migrated.
- Ground truth is evaluator-only.
- Task, output, tool-call, and run-log validation passes.
- The same model and generation settings are configured for all frameworks.
- Dataset caches are available.
- One smoke test passes for each framework.
- Experiment ID and model metadata are recorded.
