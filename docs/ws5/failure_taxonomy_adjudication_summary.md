# Failure Taxonomy and Adjudication — Lanfang Deliverable (WS5)

Status: **Methodology complete; case-level counts pending v2.0 scored outputs**
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
| **Symptom** | `failure_mode` in result JSONL; E5 failure classes per `e5_gold_semantics_v0.3.md` | Tables, aggregates (Chloe-owned definitions) |
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
| **P0** | Safety-critical wrong action (H2 under-triage, H5 comply, E3 unauthorized refund) | Main findings; dashboard callouts only if Chloe approves |
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
7. **Aggregate boundary** — Do not publish symptom/root-cause counts unless Chloe
   approves definitions for Mickey's tables.

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

Do not classify or count toward pilot failure analysis:

- v1.x and preliminary engineering smoke (`technical_smoke_only`)
- Readiness preflights (24 logical runs)
- Illegal attempt-2 retries (non-infrastructure)
- Rows on Chloe's QA exclusion list
- Invalidated framework sweeps (E5 >5% error policy)
- Stress-test runs (out of formal delivery scope)

---

## Deliverable status

| Item | Status |
|---|---|
| Taxonomy methodology | Complete |
| Adjudication workflow | Complete |
| Case-level root-cause assignments | **Pending** Chloe scored outputs + v2.0 gate |
| Aggregate symptom/root-cause tables | **Pending** Chloe aggregate definitions |
| Owner-approved case studies for report | **Pending** C1–C3 review cycle |
