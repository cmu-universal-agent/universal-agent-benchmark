# Dataset and Gold-Generation Plan

Status: schema field design approved by Chloe on 2026-07-16. H2 and H4 draft
source specifications have been received; remaining task templates and formal
approval are pending. This document is not benchmark data and is not approval
for bulk conversion.

## Confirmed Generation Methods

| Task | Gold method | Evaluation owner | Engineering owner | Current blocker |
|---|---|---|---|---|
| H1 | Automatically derived from public source data | Chloe confirms source semantics | Jessica implements converter | Exact dataset version/source fields |
| H2 | Automatically derived from HealthBench physician category plus scoped rubric rules | Chloe confirms urgency mapping | Jessica implements converter and coverage check | Approve draft difficulty thresholds and review the urgent/routine/self-care subclassification |
| H4 | Programmatic extraction from ACI-Bench notes | Chloe confirms extraction semantics/audit | Jessica implements extractor | Approve draft extraction/difficulty rules and review generated samples |
| H5 | Chloe manually designs `clarify` and `escalate` cases | Chloe authors gold and rubric | Jessica validates and packages cases | First reviewed cases and rubric |
| E1 | Automatically derived from public source data | Chloe confirms trend-label semantics | Jessica implements converter | Exact aggregation/normalization rules |
| E2 | Automatically derived from public source data | Chloe confirms recommendation gold semantics | Jessica implements converter | Candidate-set and relevance rules |
| E3 | Automatically derived from public source data | Chloe confirms policy-decision mapping | Jessica implements converter | Dataset version and ambiguous-policy handling |
| E5 | Automatically derived from public source/simulator state | Chloe confirms success/final-state semantics | Jessica implements converter; integration owner confirms simulator | Final simulator fields/status values |

## Required Source Specification

Before implementing one task-specific converter, record:

1. Dataset name, release/version, public source URL, and license/access notes.
2. Source record ID and original split fields.
3. Agent-visible input fields and evaluator-only source fields.
4. Exact raw-label/value transformation into benchmark gold.
5. Normalization rules, missing-value handling, and exclusion criteria.
6. Ambiguous/unmapped-record policy. The default is to reject conversion.
7. Gold generator/extractor version and deterministic configuration.
8. Review sample size and audit acceptance criteria.

HealthBench H2 has no native source split. Its loader's optional random sample
is not treated as a benchmark split. The converter omits `source_split`, uses
`prompt_id` as the source record ID, and applies the shared deterministic
development/pilot/validation/test split only after the mapping and difficulty
rule are approved.

The received H4 draft uses ACI-Bench's existing source splits and maps them to
development/pilot/validation/test. The held-out test files remain locked. The
specification is committed for review with `status: draft_pending_approval`;
it is not yet authorization for bulk extraction.

## Implementation Sequence

1. Chloe supplies or approves the source specification; no code is required
   from Chloe.
2. Jessica implements a deterministic converter/extractor and unit fixtures.
3. The converter generates 5–10 evaluator-only sample records per task.
4. Chloe audits the samples and requests mapping/rubric corrections.
5. Jessica runs mapping coverage, leakage, schema, and split-manifest checks.
6. Only after sample approval does bulk conversion run.

## Quality Rules

- Generated gold never enters `benchmark_case.schema.json` or adapter input.
- Every gold record retains dataset/version, source record ID, method, and
  generator version for reproducibility.
- H4 extraction is not considered validated merely because it is
  programmatic; field-level audit is required before bulk use.
- H5 manual cases must cover both `clarify` and `escalate` and include an
  explicit rubric and rationale.
- Generated records with missing or unmapped source values are rejected rather
  than silently coerced.
- All sample and bulk outputs pass schema and leakage validation.
