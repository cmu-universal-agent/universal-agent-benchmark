# Main Findings — Lanfang Deliverable (WS5)

Status: **Empirical findings pending v2.0 scored outputs**
Owner: Lanfang Hai
Prepared: 2026-08-18; revised 2026-08-18 (deduped against limitations deliverable)
For: Mickey — report findings section

---

## Gate status

| Check | Status |
|---|---|
| v2.0 formal experiment ID frozen | **Pending** written confirmation (A0) |
| Chloe scored outputs + failure candidates | **Not received locally** |
| 228 controlled-pilot rows eligible for analysis | **Pending** |
| Empirical findings (F1–F6 below) | **Blocked until gate + data** |

Do not paste F1–F6 into the public report until the gate row above is complete and
Chloe's QA package is linked.

---

## Scope statements (do not duplicate limitations)

The protocol-scope bullets previously listed here as L1–L3 are **already covered**
in `limitations_deliverable.md` (claim boundary + protocol limitations). Paste that
file once into report § **Limitations and claim boundary** only.

For the **findings / discussion** section before empirical results exist, Mickey
may use this single bridge sentence if helpful:

> This controlled pilot reports task-specific outcomes under a frozen 60-case,
> single-model protocol without a composite framework score; failure narratives
> separate runtime symptoms from WS5 root-cause attribution (see limitations and
> failure-taxonomy appendix).

Do **not** also paste the full limitations text into findings.

---

## Empirical findings (fill after Chloe handoff)

Replace `[TBD]` with v2.0 rows only. Each finding needs case ID, framework(s),
symptom, root-cause category, and one narrow claim.

### F1 — Safety or policy (P0 if present)

`[PENDING]` On `[case_id]`, `[framework]` produced `[symptom]` while `[contrast]`.
Root cause: `[category]`. Narrow claim: `[one sentence]`.

### F2 — Cross-framework divergence (P1)

`[PENDING]` For `[case_id]`, `[framework X]` vs `[framework Y]` diverged under frozen
config. Root cause: `[framework_adapter | model_formatting]`. **Only if both
framework sweeps are valid.**

### F3 — Representative repeat behavior (P1 or stability note)

`[PENDING]` Representative `[case_id]` on `[framework]` was `[consistent |
inconsistent]` across repeat logical runs 1–3. Describe symptom-layer variation only.

### F4 — Formatting vs capability (P1/P2)

`[PENDING]` On `[task_id]`, `[output_schema_invalid | instruction_drift]` occurred
without content gold mismatch.

### F5 — Evaluator boundary

`[PENDING — Chloe written approval required before report inclusion]` Borderline
`[task]` at `[metric]` → `evaluator_or_gold`. No strong causal claim until resolved.

### F6 — Repeat stability (encouraged when observed)

`[PENDING]` Representative `[case_id]` on `[framework]` remained consistent across
repeats 1–3 at `[metric/symptom layer]`.

---

## Selection worksheet

See `docs/failure_analysis_and_limitations_draft.md` §4 when data arrives.

Priority targets:

1. Any P0 safety/policy case Chloe flags
2. Strongest cross-framework divergence on a non-invalidated sweep
3. One representative-case repeat pattern (instability **or** stability)
4. One E5 row adjudicated through v0.3 semantics
5. One H5 row with criterion annotations attached

---

## Handoff to Mickey

| Now | After gate + Chloe |
|---|---|
| `limitations_deliverable.md` → § Limitations | F1–F6 (approved subset) → § Main findings |
| `failure_taxonomy_adjudication_summary.md` → appendix | Redacted case studies (local filenames) |
| Optional bridge sentence above → discussion | |
