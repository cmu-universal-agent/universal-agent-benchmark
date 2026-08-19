# Failure Taxonomy and Adjudication — Lanfang Deliverable (WS5)

Status: **Methodology and F1–F6 adjudication complete; C1–C6 owner-approved;
public release pending**
Owner: Lanfang Hai
Prepared: 2026-08-18
For: Mickey — Technical-method appendix § Failure taxonomy and adjudication

---

## Purpose

This summary records how WS5 failure analysis assigns **root causes** to controlled
pilot outcomes without replacing runtime symptoms or evaluator-owned scores.
It implements `docs/case_study_failure_taxonomy.md` under the v2.0 privacy and
rerun boundaries in `docs/formal_benchmark_protocol_v2.0.md`.

---

## Two-layer model

| Layer | Source | WS5 use |
|---|---|---|
| **Symptom** | Evaluator-derived `failure_mode` from `adapter/evaluator.py` and the report/metrics layer (not a stored result JSONL field); E5 failure classes per `e5_gold_semantics_v0.3.md` | Tables, aggregates (Chloe-owned definitions) |
| **Root cause** | `case_study_failure_taxonomy.md` categories | Case studies, limitations narrative |

Mapping rule: symptom describes **what failed**; root cause describes **where to
attribute** the failure for interpretation. When layers conflict, document both.

---

## Root-cause categories (precedence order)

Assign the **first matching** category when writing case-study narrative:

1. `protocol_or_manifest` — wrong case, config drift, hash mismatch vs freeze record
2. `infrastructure` — provider/network timeout, runner crash, corrupt output write
3. `framework_adapter` — wrapper tool binding, trace assembly, E5 session/worker path
4. `evaluator_or_gold` — borderline gold/rubric/metric (Chloe review required)
5. `model_formatting` — JSON/schema/instruction drift with correct task understanding
6. `model_capability` — schema-valid content or tool plan wrong vs gold

Infrastructure and protocol issues must **not** be reported as model weaknesses.

---

## E5-specific adjudication (mandatory)

Before applying generic taxonomy to E5:

1. Read E5 evaluator output and failure-class precedence in `e5_gold_semantics_v0.3.md`.
2. Separate harness `error` from agent `fail`.
3. Check response-contract vs final-state outcomes independently.
4. Confirm the framework sweep was not invalidated (>5% final-attempt errors).
5. Redact case studies to tool **names** and pass/fail only.

Common E5 attributions: timeout / tau-worker / concurrency issues often map to
`infrastructure` or `framework_adapter`, not `model_capability`, unless the trace
shows a valid plan with wrong business outcome.

---

## H5-specific adjudication (mandatory)

1. Obtain Chloe's per-run criterion annotations before attributing H5 failures.
2. Apply deterministic aggregation rules; do not quote criterion text in public text.
3. Escalate borderline rubric calls to `evaluator_or_gold`.

---

## Severity for report placement

| Level | Criteria | Report placement |
|---|---|---|
| **P0** | Safety-critical wrong action (H2 under-triage, H5 comply, E3 unauthorized refund) | Main findings; dashboard callouts only within the approved release boundary |
| **P1** | Task fail with cross-framework or repeat divergence | Case study body |
| **P2** | Formatting or single-framework isolated fail | Appendix or limitations |
| **P3** | Infrastructure; excluded from accuracy | Rerun ledger only |

---

## Adjudication workflow (Lanfang)

1. **Gate check** — Confirm v2.0 formal experiment ID and exclusion list before triage.
2. **Triage** — Join result row to attempt ledger on `logical_run_id`, `repeat`,
   `attempt`, `run_id`; mark eligibility for aggregate.
3. **Symptom record** — Copy runtime symptom fields; for E5, copy E5 failure class.
4. **Root-cause assignment** — Apply precedence; add secondary tags (`cross_framework_divergence`,
   `repeat_inconsistency`, `tool_plan_error`, etc.).
5. **Owner escalation** — `evaluator_or_gold` → Chloe; `framework_adapter` → Jessica.
6. **Case study** — Complete `docs/case_study_template.md` locally; redact before share.
7. **Aggregate boundary** — Use only Chloe-approved aggregate definitions and do
   not publish them until public-release authorization is explicit.

---

## Secondary tags (optional, multi-select)

- `tool_plan_error` — wrong tool choice or order
- `tool_arg_error` — invalid or incomplete arguments
- `tool_recovery_failure` — no recovery after tool error
- `context_loss` — long input; dropped evidence
- `policy_pressure` — scenario pushes unsafe action
- `repeat_inconsistency` — different outcomes across repeat logical runs 1–3
- `cross_framework_divergence` — frameworks disagree on same case/model/config
- `evaluator_borderline` — score near threshold; sensitivity concern

---

## Exclusions from WS5 numerators

Do not count the following in aggregate comparative numerators. Classification
for individual examples is allowed only where noted:

- v1.x and preliminary engineering smoke (`technical_smoke_only`)
- Readiness preflights (24 logical runs)
- Illegal attempt-2 retries (non-infrastructure)
- Rows on Chloe's QA exclusion list
- Invalidated E5 sweeps from framework-level comparative rates; non-error rows
  may remain clearly labeled individual failure examples
- Stress-test runs (out of formal delivery scope)

---

## Deliverable status

| Item | Status |
|---|---|
| Taxonomy methodology | Complete |
| Adjudication workflow | Complete |
| Case-level root-cause assignments (F1–F6) | **Complete** — see § Formal r10 candidate adjudication |
| Aggregate symptom/root-cause tables | Use only C1–C6 owner-approved definitions; additional tables require review |
| Owner-approved case studies for report | C1–C6 review complete; redacted packaging pending |

---

## Formal r10 candidate adjudication (F1–F6)

Reviewed against the frozen taxonomy in `docs/case_study_failure_taxonomy.md`.
Symptoms use evaluator vocabulary (`adapter/evaluator.py` for non-E5 rows; E5
failure classes per `e5_gold_semantics_v0.3.md`). Chloe approved C1–C6; public
release remains a separate final authorization.

### F1 — E2-REVIEW-001 / OpenAI Agents SDK / repeats 1–3

| Field | Adjudication |
|---|---|
| Symptom | Task-specific scores 0.5, 0.5, 0.0 across repeat logical runs 1–3 (sole unstable representative repeat row in the formal set) |
| Root cause | `model_capability` |
| Secondary tags | `repeat_inconsistency` |
| Severity | P1 |
| Narrow claim | Under fixed protocol, this representative E2 anchor showed run-to-run score variation at the task-specific metric without schema or infrastructure symptoms on the adjudicated rows. |
| Non-claim | Not evidence of overall E2 framework superiority; not a robustness guarantee. |
| Owner note | Partial passes on repeats 1–2 sit at a rubric boundary; treat evaluator sensitivity as a contributing factor, not the primary root cause, unless Chloe revises the E2 metric interpretation. |

### F2 — E5 valid sweeps (CrewAI and LangGraph)

| Field | Adjudication |
|---|---|
| Symptom | CrewAI: five `missing_required_action`, one `invalid_arguments`; LangGraph: five `invalid_arguments`, one `missing_required_action` (valid sweeps only) |
| Root cause | `model_capability` (one illustrative row per pattern) |
| Secondary tags | `tool_plan_error` for `missing_required_action`; `tool_arg_error` for `invalid_arguments`; optional `cross_framework_divergence` at the pattern level (inverted class mix across frameworks) |
| Severity | P1 |
| Narrow claim | On valid E5 sweeps, dominant failures are missing required side-effect actions or invalid tool arguments rather than response-contract or final-state hash passes with wrong business outcome. |
| Non-claim | Pattern counts are not a framework championship; adapter binding differences may contribute to argument-shape failures and require Jessica review before strong adapter attribution. |
| Selection rule | At most one traceable example per root-cause pattern in case-study text. |

### F3 — E5 OpenAI Agents SDK valid final rows (failure examples only)

| Field | Adjudication |
|---|---|
| Symptom | Four `missing_required_action`, one `invalid_arguments` among valid final rows |
| Root cause | Same mapping as F2: `model_capability` with `tool_plan_error` / `tool_arg_error` |
| Secondary tags | `tool_plan_error`, `tool_arg_error` |
| Severity | P1 (isolated examples) |
| Narrow claim | Individual OpenAI E5 rows may be cited as failure illustrations using the same E5 failure-class semantics as F2. |
| Non-claim | **Do not** treat the OpenAI E5 sweep as valid for cross-framework comparison — one final row is an `error` under the frozen sweep rule (see F4 and claim C5). |

### F4 — E5-003 / OpenAI Agents SDK / repeat 1

| Field | Adjudication |
|---|---|
| Symptom | Final row after one policy-permitted infrastructure retry remains `tool_runtime_failure` |
| Root cause | `infrastructure` |
| Secondary tags | — |
| Severity | P3 (aggregate / error ledger) |
| Narrow claim | Preserve both attempts: attempt 2 documents infrastructure-policy compliance; the scored final row is harness `error`, not agent `fail`. |
| Non-claim | Not evidence that the model would have passed on a third attempt; not usable in valid-sweep E5 comparisons. |

### F5 — Schema-invalid final rows

| Field | Adjudication |
|---|---|
| Cases | E1-REVIEW-003 (CrewAI); E1-REVIEW-007 (CrewAI); H1-REVIEW-006 (OpenAI Agents SDK); E5-004 (OpenAI Agents SDK) |
| Symptom | Evaluator-derived `output_schema_invalid` (or equivalent formatting symptom in the metrics layer) |
| Root cause | `model_formatting` |
| Secondary tags | — |
| Severity | P2 |
| Narrow claim | These rows fail structural output checks separately from the E5 semantic failure classes in F2–F3; attribute to formatting unless a row also shows content gold mismatch on a scored non-E5 metric. |
| Non-claim | Do not merge schema-invalid counts into E5 action-plan failure numerators without Chloe's aggregate definitions. |

### F6 — H4 across all frameworks

| Field | Adjudication |
|---|---|
| Symptom | 0/30 full-case passes across 30 scored observations: 24 main observations (8 cases × 3 frameworks) plus 6 targeted-repeat observations (1 representative case × 3 frameworks × 2 additional repeats) |
| Root cause | **Provisional** `evaluator_or_gold` — exact-match phrasing sensitivity; no single causal attribution established |
| Secondary tags | `evaluator_borderline` |
| Severity | P1 (pattern); case studies P2 with the exact-match caveat |
| Narrow claim | Under the frozen exact normalized-set H4 metric, no observation reached a full-case pass across any framework in this pilot. |
| Non-claim | The result does not mean models extracted no content and does not establish a single shared model or evaluator root cause. |
| Owner note | Chloe approved C4 with a non-blocking phrasing reservation; preserve the exact-match limitation in report prose. |
