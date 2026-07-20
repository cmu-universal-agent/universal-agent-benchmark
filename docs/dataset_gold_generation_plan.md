# Dataset and Gold-Generation Plan

Status: schema field design approved by Chloe on 2026-07-16. Chloe's H2/H4 v2
feedback, four owner-authored H5 cases, and the E3 pending-order exclusion were
incorporated on 2026-07-20. Chloe subsequently confirmed H2-004 unchanged as
`routine`, closing H2 urgency-label review. H2 remains draft only for its
difficulty metadata: Chloe offered no threshold-adjustment recommendation and
Jessica chose to retain the current provisional rule for now and revisit it
later. This does not block H2 gold generation. H4 and the H5 case rubrics still
require follow-up review. This document is not benchmark data and is not
approval for bulk conversion.

## Confirmed Generation Methods

| Task | Gold method | Evaluation owner | Engineering owner | Current blocker |
|---|---|---|---|---|
| H1 | Automatically derived from public source data | Chloe confirms source semantics | Jessica implements converter | Exact dataset version/source fields |
| H2 | Automatically derived from HealthBench physician category plus scoped timeframe rules and evaluator-only owner overrides | Chloe confirms urgency mapping | Jessica implements converter and coverage check | No gold blocker; current difficulty rule retained provisionally and scheduled for later calibration |
| H4 | Programmatic extraction from ACI-Bench notes using header, problem-block, and semantic routing rules | Chloe confirms extraction semantics/audit | Jessica implements extractor | Review regenerated v2 samples and approve extraction/difficulty rules |
| H5 | Chloe manually designs `clarify` and `escalate` cases | Chloe authors gold and rubric | Jessica validates and packages cases | Four draft cases supplied (2 clarify, 2 escalate); second-pass rubric review required |
| E1 | Automatically derived from public source data | Chloe confirms trend-label semantics | Jessica implements converter | Exact aggregation/normalization rules |
| E2 | Automatically derived from public source data | Chloe confirms recommendation gold semantics | Jessica implements converter | Candidate-set and relevance rules |
| E3 | Automatically derived from public source data | Chloe confirms policy-decision mapping | Jessica implements converter | `cancel_pending_order` exclusion approved; remaining source/version rules still require normal audit |
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

HealthBench H2 has no native train/test split. Its main eval file is recorded as
`source_split: main_eval`, which is provenance rather than a benchmark split.
The converter uses `prompt_id` as the source record ID and preserves Chloe's
reviewed source selection in a local evaluator-only decision file. That file is
gitignored and must never be published with benchmark cases.

The H4 v2 draft uses ACI-Bench's existing source splits and maps them to
development/pilot/validation/test. It now handles abbreviated CC/HPI headers,
newline-separated ROS entries, HPI history supplements, boilerplate removal,
and semantic problem-title routing. The held-out test files remain locked. The
specification remains `draft_pending_approval`; it is not yet authorization for
bulk extraction.

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
  explicit rubric and rationale. Chloe supplied two of each on 2026-07-20;
  exact case-level content stays in the local evaluator-only directory until
  its second-pass review is complete.
- E3 rejects every source scenario containing `cancel_pending_order`, including
  mixed-action scenarios. Chloe confirmed that cancellation is a deterministic
  pending-order action rather than the delivered-order policy judgment E3 is
  designed to measure; it must not map to `refund_allowed`.
- Generated records with missing or unmapped source values are rejected rather
  than silently coerced.
- All sample and bulk outputs pass schema and leakage validation.
