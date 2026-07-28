# Workstream #2: Current Status and Asynchronous Handoff

Last updated: July 16, 2026

> Historical snapshot: this handoff predates the eight deterministic core-task
> converters and strict task-output schema validation now present in PR
> #1. For the current executive snapshot, proposal/workplan index, owners, and
> gates, read `docs/PROJECT_LEAD_GUIDE.md` first.
>
> 2026-07-21 update: H2 and E3 are closed, Chloe approved H5, and H4 v4 is
> approved after the final H4-REVIEW-007 metformin-history correction. CrewAI
> integration is in separate stacked PR #2. All WS2 semantic-review gates are
> closed. PR #1 is Ready for Review, and neither PR should be merged until
> Jessica explicitly releases the current hold and repository review is
> complete.

## Purpose

This historical document lets the team continue asynchronously across time
zones. Its 2026-07-21 banner records the closed semantic review; use the
project-lead guide for current PR and WS3 gates.

## Current Snapshot

The project has a functional multi-framework base for LangGraph, CrewAI, and
the OpenAI Agents SDK. Framework dependencies are isolated, shared runtime
metadata and normalized tool traces are partially implemented, and legacy task
files remain runnable.

The five JSON Schema files are valid Draft 2020-12 schemas, and Chloe has
confirmed that no further field-design adjustments are required. The
current runtime result envelope records many of the proposed fields, but it is
not yet a complete schema-valid implementation of `run_log.schema.json`.

Generated JSONL results remain local and gitignored. A controlled no-tool smoke
task has run successfully through all three adapters with the same configured
model. The strict evaluator correctly reported CrewAI's missing terminal period
as instruction drift instead of a full instruction-following pass. This is an
infrastructure result, not a comparative framework score.

### Pilot Terminology: Eight Tasks vs. Twenty Cases

The first-batch scope contains eight **task types**: H1, H2, H4, H5, E1, E2,
E3, and E5. This does not mean eight total benchmark records.

The repository currently contains twenty legacy-compatible **cases**: ten
medical cases that primarily exercise H1 and ten e-commerce trend cases that
primarily exercise E1. They cover two of the eight core task types. The choice
is therefore not "eight tasks or twenty cases." The next contract smoke test
needs at least one synthetic fixture for each of the eight task types, while
the existing twenty cases remain useful for H1/E1 compatibility regression.

Synthetic contract fixtures are infrastructure tests only and must not be
reported as benchmark scores.

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
- Added local draft contract fixtures for all eight core task output shapes,
  valid/invalid schema cases, tool success/failure, and run success/failure.
- Added framework-neutral checks for aggregate context length, evaluator-data
  leakage, tool-result truncation metadata, deterministic split manifests, and
  dataset-label mapping coverage.
- Added machine-readable smoke-task evaluation rules for required keys, exact
  values, and one-sentence output constraints.
- Added provider-reported token usage collection for all three adapters.

## Validation Completed

- 23 Python files passed syntax parsing.
- All five schema files passed JSON Schema definition checks.
- The Benchmark Case Schema v1.0 example passed formal validation.
- Legacy and v1.0 task loading passed.
- Tool filtering passed for all three frameworks.
- Dataset overwrite guards passed.
- `--require-v1` correctly blocks a formal run while legacy tasks remain.
- Contract fixtures passed: 14 valid, 11 intentionally invalid, five schemas.
- Adapter contracts passed for legacy/v1 loading, tool-result truncation,
  split manifests, mapping coverage, aggregate limits, and leakage checks.
- Shared tool contracts passed for no-tool, success, and failure paths.
- The latest clean live smoke (`ws2-smoke-clean-20260716-03`) recorded valid
  JSON and token usage for OpenAI Agents SDK, LangGraph, and CrewAI.

## Current Blockers and Pending Decisions

### Waiting for Chloe

- Provide the exact public dataset/version, source gold fields, normalization
  rules, and unmapped-record policy for H1, H2, E1, E2, E3, and E5.
- Confirm the H4 programmatic extraction specification and audit criteria.
- Provide the first H5 `clarify` and `escalate` manual cases plus their rubric.
- Return the completed dataset/gold templates so Jessica can implement the
  task-specific converters and generate review samples.
- H2 draft received: HealthBench `prompt_id`, raw tag format, and measured
  physician-category distribution are now documented. Approve the provisional
  difficulty thresholds and review the keyword subclassification for
  urgent/routine/self-care before bulk conversion.
- H4 draft received: ACI-Bench source fields, header aliases, four-field
  extraction rules, and source-split mapping are documented. Approve the
  extraction/difficulty rules and review generated samples before bulk use.

### Chloe Gold-Generation Decision (2026-07-16)

- Chloe confirmed that the current schema requires no further field changes.
- H1, H2, E1, E2, E3, and E5 gold values will be generated automatically
  from public datasets.
- H4 structured gold fields will be extracted programmatically from the source
  clinical record.
- Chloe will manually design H5 `clarify` and `escalate` cases.
- Chloe does not need to convert or label every record. Jessica owns the
  converters, benchmark-field generation, split manifests, coverage checks,
  schema validation, and review samples.

The field design is now approved. H2 and H4 have detailed owner-provided draft
specifications, while the other task-specific templates remain pending. Bulk
conversion remains blocked until each applicable specification is approved and
the first generated samples pass owner review.

### After Chloe's Review

- Implement dataset-specific converters/extractors and unit fixtures.
- Generate 5–10 evaluator-only review samples per task for Chloe.
- After sample approval, run bulk conversion plus mapping coverage, leakage,
  schema, and split-manifest validation.
- Migrate the selected pilot cases to formal Benchmark Case Schema v1.0.
- Run the eight-task controlled pilot across all three frameworks.

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

- Complete and review `frameworks/crewai_agent/` integration ownership.
- Verify Windows/Linux requirements and unified `BenchmarkTask` /
  `AgentRunResult` compatibility.
- Validate `allowed_tools` plus no-tool, tool-success, and tool-failure paths.
- Document CrewAI support for token usage, tool calls, errors, latency, and
  model metadata, including known gaps.
- Prepare the CrewAI entry point for the eight core tasks once converted cases
  are ready.
- Confirm the integration sequence and the number of cases per task type in
  the first controlled pilot.

### Jessica

- WS2 work that does not depend on dataset semantics is complete locally:
  schemas, contracts, compatibility, strict smoke evaluation, shared tool
  paths, token metadata, and the first three-framework smoke run.
- After Chloe returns approved templates, implement converters, generate
  review samples, and run coverage/schema/leakage/split validation.
- After the eight formal task cases are available, run the first controlled
  three-framework pilot and inspect comparable result fields.

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
- Eight core pilot tasks selected and migrated. *(Pending dataset templates.)*
- Ground truth is evaluator-only.
- Task, output, tool-call, and run-log validation passes. *(Contract layer
  passes; formal converted-task validation remains pending.)*
- The same model and generation settings are configured for all frameworks.
- Dataset caches are available. *(Pending converter inputs.)*
- One smoke test passes for each framework.
- Experiment ID and model metadata are recorded.
