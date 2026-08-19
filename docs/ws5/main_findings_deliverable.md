# Main Findings — Lanfang Deliverable (WS5)

Status: **F1–F6 and C1–C6 owner-approved; public release pending**
Owner: Lanfang Hai
Prepared: 2026-08-18; revised 2026-08-19 (formal r10 gate sync + F1–F6 adjudication)
For: Mickey — report findings section

---

## Gate status

| Check | Status |
|---|---|
| v2.0 formal controlled pilot execution | **Complete** — 228/228 logical runs scored |
| H5 human criterion annotations | **Complete** — 30/30 applied |
| Privacy boundary (no forbidden fields in shared deliverables) | **Confirmed** |
| Public aggregate claims (C1–C6) | **Approved** by Chloe; C4 has a non-blocking phrasing reservation |
| Empirical findings (F1–F6 below) | **Approved for final integration; public release still pending** |

F1–F6 may now enter the final report draft, but public release remains a separate
authorization. Narrative below uses case IDs and frameworks only — no raw
prompts, gold, traces, run IDs, hashes, or private paths.

---

## Scope statements (do not duplicate limitations)

The protocol-scope bullets previously listed here as L1–L3 are **already covered**
in `limitations_deliverable.md` (claim boundary + protocol limitations). Paste that
file once into report § **Limitations and claim boundary** only.

For the **findings / discussion** section, Mickey may use this bridge sentence:

> This controlled pilot reports task-specific outcomes under a frozen 60-case,
> single-model protocol without a composite framework score; failure narratives
> separate runtime symptoms from WS5 root-cause attribution (see limitations and
> failure-taxonomy appendix).

Do **not** also paste the full limitations text into findings.

---

## Empirical findings — formal r10 candidate adjudication (F1–F6)

Each finding lists case ID, framework(s), symptom, root-cause category, and one
narrow claim. Full methodology and secondary tags: `failure_taxonomy_adjudication_summary.md`.

### F1 — Representative repeat instability (E2-REVIEW-001)

On **E2-REVIEW-001** with **OpenAI Agents SDK**, task-specific scores were
**0.5, 0.5, 0.0** across repeat logical runs 1–3 — the only unstable row among
24 representative targeted repeats (23/24 stable under the frozen score).

Symptom: partial pass then full fail at the task-specific metric layer.
Root cause: **`model_capability`**. Secondary: **`repeat_inconsistency`**.
Narrow claim: fixed-protocol run-to-run variation on this E2 anchor without
schema or infrastructure symptoms on the adjudicated rows.
**Not** an overall E2 framework ranking.

### F2 — E5 valid-sweep failure patterns (CrewAI, LangGraph)

On **valid E5 sweeps**, CrewAI final rows show five **`missing_required_action`**
and one **`invalid_arguments`**; LangGraph shows five **`invalid_arguments`** and
one **`missing_required_action`**.

Symptom: E5 failure classes per v0.3 semantics.
Root cause: **`model_capability`** (one illustrative example per pattern).
Secondary: **`tool_plan_error`**, **`tool_arg_error`**; optional pattern-level
**`cross_framework_divergence`**.
Narrow claim: dominant E5 failures on valid sweeps are missing required actions or
invalid tool arguments, not passed response-contract with wrong final state.
Select at most one traceable example per pattern in case-study text.

### F3 — E5 OpenAI Agents SDK rows (failure examples only)

Among **OpenAI Agents SDK** E5 valid final rows: four **`missing_required_action`**,
one **`invalid_arguments`**. These counts describe semantic symptoms and include
E5-004; they do not assign a second primary root cause to that row.

Root cause: **`model_capability`** with tool-plan / tool-arg tags for the four
rows other than E5-004. E5-004 is excluded from this primary attribution and
uses **`model_formatting`** in F5, following the frozen taxonomy precedence.
Narrow claim: individual rows may illustrate E5 failure-class semantics.
**Non-claim:** the OpenAI E5 sweep is **invalid** for cross-framework comparison
(one final **`error`** row — see F4 and claim C5).

### F4 — E5 infrastructure error boundary (E5-003)

On **E5-003** / **OpenAI Agents SDK** / repeat 1, attempt 2 (after one
documented infrastructure-eligible retry) remained **`tool_runtime_failure`**.

Symptom: harness **`error`**, not agent **`fail`**.
Root cause: **`infrastructure`**. Severity P3.
Narrow claim: preserve both attempts — retry shows policy compliance; final row
is an error disposition, not a scored agent failure comparable to F2/F3 rows.

### F5 — Formatting vs capability (schema-invalid rows)

Four schema-invalid final rows: **E1-REVIEW-003** (CrewAI), **E1-REVIEW-007**
(CrewAI), **H1-REVIEW-006** (OpenAI Agents SDK), **E5-004** (OpenAI Agents SDK).

Symptom: evaluator-derived **`output_schema_invalid`** in the metrics layer.
Root cause: **`model_formatting`**. Severity P2.
Narrow claim: structural output failure is the single primary attribution for
E5-004 even though F3 also records its E5 semantic symptom; other rows remain
separate from content gold mismatch unless they also fail scored content metrics.

### F6 — H4 exact-match interpretation boundary

**H4** across all frameworks: **0/30** full-case passes across 30 scored
observations: 24 main observations (8 cases × 3 frameworks) plus 6
targeted-repeat observations (1 representative case × 3 frameworks × 2
additional repeats).

Symptom: zero full-case pass under the frozen exact normalized-set H4 metric.
Root cause: **provisional `evaluator_or_gold`** because exact-match phrasing
sensitivity remains a limitation; no single causal attribution is established.
Narrow claim: no full-case H4 pass in this pilot under the frozen metric.
**Non-claim:** this does not mean models extracted no content and does not prove a
single shared model or evaluator root cause. Chloe approved C4 with a
non-blocking phrasing reservation.

---

## Selection worksheet (completed targets)

| Priority | Candidate | Status |
|---:|---|---|
| 1 | F1 repeat instability | Adjudicated |
| 2 | F2 E5 valid-sweep patterns | Adjudicated |
| 3 | F3 E5 OpenAI examples (non-comparative) | Adjudicated |
| 4 | F4 E5-003 error boundary | Adjudicated |
| 5 | F5 schema-invalid separation | Adjudicated |
| 6 | F6 H4 zero full-case pass | Adjudicated (provisional root cause) |

Additional case studies beyond these six may be drafted locally from
`docs/case_study_template.md`; keep them private until release authorization.

---

## Handoff to Mickey

| Final draft integration | Public-release boundary |
|---|---|
| `limitations_deliverable.md` → § Limitations | Release only after explicit authorization |
| F1–F6 approved subset → § Main findings | Keep raw cases, gold, and traces private |
| `failure_taxonomy_adjudication_summary.md` → appendix | Publish only approved aggregate captions |
