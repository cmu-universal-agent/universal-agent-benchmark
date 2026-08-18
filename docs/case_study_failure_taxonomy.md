# Case Study Failure Taxonomy

Status: **Frozen for WS5 controlled-pilot failure analysis**
Owner: Lanfang Hai
Prepared: 2026-08-04; status updated 2026-08-18 (semantics unchanged since PR #25)
Related: `docs/stress_failure_rubric.md` (stress-only; out of formal delivery scope)

## Purpose

Classify failures observed in the **228-logical-run controlled pilot** (180
main-pilot runs plus 48 targeted repeats) so case studies can attribute
outcomes to the correct layer: model, framework adapter, evaluator, or
infrastructure. The separate 24 readiness preflights bring the execution plan
to 252 logical runs but are not controlled-pilot result rows. Retry attempts do
not create additional logical runs.

This taxonomy is for **analysis and limitations**, not for replacing the
`failure_mode` derived by the evaluator/report layer.

Use this document when writing case studies, failure-analysis sections, and
limitations. Do not merge stress-test failures into standard pilot accuracy.

## Relationship to evaluator failure modes

`adapter/evaluator.py` derives one primary `failure_mode` after reading a result
row. The current vocabulary is `runtime_exception:<error_type>`,
`invalid_json`, `missing_required_keys`, `output_schema_invalid`,
`instruction_drift`, `tool_overuse`, and `ok`. It is not stored as a runtime
field in the result JSONL. `timeout` is an attempt-ledger status, and
`task_accuracy_failure` is not in the evaluator vocabulary.

The case-study taxonomy adds a **root-cause layer** and optional **secondary
tags** for narrative analysis.

Mapping rule:

- Evaluator-derived `failure_mode` or attempt status → primary symptom.
- Case-study **root_cause_category** → why the symptom occurred.
- When multiple layers contribute, pick the **earliest preventable layer** as
  primary root cause and list others as contributing factors.

## Root cause categories

### 1. `model_capability`

The framework executed correctly; the model produced wrong content, unsafe
content, or incoherent tool plans.

Examples:

- H1 wrong PubMedQA decision with valid JSON.
- H2 under-triage (urgency too low) with schema-valid output.
- E2 recommendations violate stated constraints.
- E5 wrong tool sequence but trace structure is valid.

Evidence: schema-valid output; tool calls well-formed; gold/evaluator mismatch
on content or actions; other frameworks with same model may fail similarly.

### 2. `model_formatting`

The model understood the task but failed output or tool-call formatting.

Examples:

- Markdown-wrapped JSON, extra prose, wrong key names.
- Boolean encoded as string against prompt rules.
- Missing required top-level keys.

Evidence: maps to runtime `invalid_json`, `output_schema_invalid`,
`missing_required_keys`, or `instruction_drift` without gold mismatch on
semantics.

### 3. `framework_adapter`

The shared task and gold are correct; the framework wrapper mishandles tools,
state, traces, or final output assembly.

Examples:

- Tool schema binding rejects valid arguments (LangGraph Pydantic mismatch).
- OpenAI Agents SDK drops or reorders tool results in `final_output`.
- CrewAI tool wrapper does not forward to shared retail core.
- E5 session not reset between steps; stale simulator state.

Evidence: same model prompt succeeds on another framework; shared-core offline
evidence passes but live wrapper trace differs; reproduction isolated to
`frameworks/*/run.py` or `*_retail_run.py`.

### 4. `evaluator_or_gold`

The agent behavior may be reasonable; scoring or gold semantics disagree.

Examples:

- H4 extraction gold omits phrasing the owner later approved.
- E3 `needs_review` vs `return_allowed` borderline mapping.
- E5 response-contract keyword match too strict/loose.
- Rubric false positive on `unsafe_response`.

Evidence: manual owner review overturns automated score; evaluator version
change fixes without model change; disagreement only on metric boundary.

**Handling:** do not silently change gold. Escalate to Chloe, record deviation
in the rerun ledger, and exclude from aggregate until resolved.

### 5. `infrastructure`

Environment, provider, or runner failure unrelated to agent quality.

Examples:

- API rate limit, proxy timeout, DNS failure.
- Runner crash, OOM, subprocess exit non-zero.
- Missing venv, wrong Python version, corrupted output file.
- E5 tau worker subprocess failure.

Evidence: maps to evaluator-derived `runtime_exception:*` or attempt-ledger
status `timeout`; empty or partial JSONL; retry succeeds with identical prompt;
permitted under the frozen rerun policy.

**Handling:** one documented retry allowed; otherwise mark `error` and exclude
from accuracy numerators per protocol.

### 6. `protocol_or_manifest`

Case, prompt, or configuration drift after freeze.

Examples:

- Wrong case file in run directory.
- Model or seed differs from frozen config.
- Evaluator version mismatch vs manifest SHA.

Evidence: audit log / manifest hash mismatch. Not a model or framework bug.

## Secondary tags (optional, multi-select)

| Tag | Meaning |
|---|---|
| `tool_plan_error` | Wrong tool choice or order |
| `tool_arg_error` | Invalid or incomplete tool arguments |
| `tool_recovery_failure` | Did not recover after tool error |
| `context_loss` | Long input; dropped evidence |
| `policy_pressure` | User/scenario pushes unsafe action |
| `repeat_inconsistency` | Different outcome across targeted repeats |
| `cross_framework_divergence` | Frameworks disagree on same case/model |
| `evaluator_borderline` | Score near threshold; sensitivity concern |

## Precedence for case study primary root cause

When diagnosing for narrative, assign the first matching category:

```text
1. protocol_or_manifest
2. infrastructure
3. framework_adapter
4. evaluator_or_gold   (only after owner review flags issue)
5. model_formatting
6. model_capability
```

Infrastructure and protocol issues must not be reported as model weaknesses.

## Severity for case study inclusion

| Level | Criteria | Report use |
|---|---|---|
| **P0** | Safety-critical wrong action (H2 under-triage, H5 comply, E3 unauthorized refund) | Main findings; figure in dashboard callouts |
| **P1** | Task fail with clear cross-framework or repeat divergence | Case study body |
| **P2** | Formatting or single-framework isolated fail | Appendix or limitations |
| **P3** | Infrastructure; excluded from accuracy | Rerun ledger only |

## Adjudication workflow

1. **Triage** from the result JSONL, attempt ledger, trace summary, and
   evaluator/report output.
2. **Classify** root cause using this taxonomy.
3. **Confirm** with Chloe if `evaluator_or_gold` is suspected.
4. **Confirm** with Jessica if `framework_adapter` is suspected.
5. **Record** in case study template (see `docs/case_study_template.md`).
6. **Do not** re-run to improve scores; only infrastructure reruns per protocol.

## Claim boundary

Case studies support **controlled pilot** observations. Do not infer full
robustness, pick an overall framework winner, or merge stress-test results into
these categories without a separate, clearly labeled section.
