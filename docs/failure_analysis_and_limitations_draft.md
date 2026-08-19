# Failure Analysis & Limitations — Lanfang Internal Checklist

Status: **Internal checklist — not the Mickey paste source**
Owner: Lanfang Hai
Prepared: 2026-08-18; revised with gate and attribution guardrails

**Mickey deliverables:** use `docs/ws5/` only (`README.md` index).
Inputs: `docs/case_study_failure_taxonomy.md`, `docs/case_study_template.md`,
`docs/representative_case_ids.md`, `docs/controlled_pilot_protocol.md`,
`docs/formal_benchmark_protocol_v2.0.md`, `docs/e5_gold_semantics_v0.3.md`,
`docs/experiment_report_skeleton.md`

This file is **Lanfang's local working draft** for Mickey's report integration.
Do not treat placeholder case-study slots as scored results until Chloe's outputs
are linked. Do not commit evaluator-only gold, raw JSONL, private hashes, or
filled-in case excerpts.

Before starting analysis, fast-forward local checkout to GitHub `main` so
protocol and representative-ID docs match the frozen WS4 record.

---

## 0. Lanfang hard rules (read first)

1. **Do not start WS5 case studies until formal scoring is confirmed.** You need
   written confirmation that v2.0 controlled-pilot logical runs are scored under
   a pinned formal experiment ID (228/228 complete as of formal r10). Public
   aggregate claims still require Chloe C1–C6 approval before report inclusion.
2. **Use v2.0 denominators only.** All analysis rows must come from the v2.0
   experiment ID in the private freeze record. Exclude every v1.x attempt,
   readiness preflight, and any run on Chloe/Mickey's exclusion list.
3. **Never invent aggregate tables.** You deliver narrative case studies and
   limitations text. Aggregate counts and dashboard figures come from Chloe and
   Xiaoxia; reconcile before Mickey locks captions.
4. **Deliver skeleton deltas, not a full report overwrite.** Paste limitations
   and failure-taxonomy text into `experiment_report_skeleton.md` as additions
   or edits to empty subsections; do not replace Mickey's live scaffold wholesale.
5. **Do not commit filled drafts.** Keep scored case-study files local or
   gitignored until redacted and owner-approved.

---

## 1. Lanfang completion plan

### Phase A — Scope lock (Lanfang verifies before writing)

| Step | Lanfang action | Wait for | Lanfang output |
|---|---|---|---|
| A0 | Request **written** gate confirmation + formal experiment ID + pinned commit | Jessica / Mickey | Gate checklist (signed off) |
| A1 | Pull v2.0 exclusion list: v1.x, preflights, invalid framework sweeps, illegal retries | Chloe / Mickey | Local exclusion table |
| A2 | Receive scored outputs + reviewed failure candidates | Chloe | Local QA package |
| A3 | Verify join keys on every row you touch: `experiment_id`, `logical_run_id`, `repeat`, `attempt`, `run_id` | — | Triage checklist |
| A4 | Confirm each candidate row is **eligible for aggregate** (latest eligible attempt; not excluded) | Chloe | Eligibility column in worksheet |

**Lanfang exit criteria before Phase B:**

- Formal v2.0 scoring confirmed (228/228 logical runs; H5 annotations complete).
- You have Chloe's failure-candidate list **and** the v2.0 exclusion list.
- Every worksheet row maps to one v2.0 controlled-pilot logical run (not preflight).
- No open data-integrity flags from Chloe (or document which tasks/frameworks remain blocked).

### Phase B — Triage, selection, and writing (Lanfang)

| Step | Lanfang action | Output |
|---|---|---|
| B1 | Tag Chloe's candidates P0–P3 using `case_study_failure_taxonomy.md` | Candidate table |
| B2 | Build repeat matrix: 8 representative IDs × 3 frameworks × repeat 1–3 | Repeat matrix |
| B3 | Shortlist 2–4 **cross-framework divergence** cases (non-representative OK) | Shortlist |
| B4 | Shortlist 1–2 **repeat-stable** representative cases if observed | Stability note |
| B5 | Select **3–5 main findings** (mix: failure, divergence, stability — not only dramatic fails) | Finding list |
| B6 | Write **4–6 case studies** via `case_study_template.md` (local files) | Redacted drafts |
| B7 | Finalize limitations four subsections (§6 below) as skeleton **delta** | Markdown for Mickey |
| B8 | Write taxonomy adjudication summary (§7 below) | 1-page summary |

**Lanfang deliverables to Mickey:**

- 3–5 evidence-backed findings (each: case ID, framework, root-cause category)
- 4–6 redacted case studies (P0/P1 in body; P2 in appendix)
- Limitations delta for `experiment_report_skeleton.md` § Limitations
- Failure taxonomy adjudication summary
- Local **exclusion list** copy (which runs you did not use and why)

### Phase C — Lanfang review and handoff

| Step | Lanfang sends to | Lanfang asks them to check |
|---|---|---|
| C1 | Chloe | `evaluator_or_gold` attributions; H5 criterion handling; no gold leak |
| C2 | Jessica | `framework_adapter` / E5 tool-path claims |
| C3 | Xiaoxia | Any number or caption you cite matches dashboard aggregates |
| C4 | Mickey | Report fit, claim boundary, skeleton paste locations |
| C5 | Lanfang | Final redaction; remove local paths from shared text |

**Finding 5 rule:** Evaluator-boundary findings may enter the report **only after
Chloe's written approval**, not as optional filler.

### Suggested timeline (Lanfang)

| When | Lanfang task |
|---|---|
| T+0 | A0–A4 gate and exclusion lock |
| T+0–1 | B1–B4 triage and worksheet |
| T+1–3 | B5–B8 drafts (allow slack if C1 blocks on evaluator disputes) |
| T+3–5 | C1–C5 review cycle |
| Before Report v0.7 | Handoff package to Mickey |

If evaluator disputes remain open, ship limitations + non-disputed case studies
first; hold disputed findings until Chloe resolves.

---

## 2. Lanfang task-specific subflows

### 2.1 E5 (mandatory extra steps)

E5 does not use the generic evaluator-derived `failure_mode` alone. For every E5 case study:

1. Read E5 evaluator output and `docs/e5_gold_semantics_v0.3.md` failure classes
   (response contract, final-state hash, harness `error` vs agent `fail`).
2. Map E5 failure class → case-study root cause (often `framework_adapter` or
   `infrastructure` for timeout/tau-worker issues; `model_capability` only when
   trace is valid and tool plan/content is wrong).
3. Check whether the framework sweep was **invalidated** (>5% final-attempt
   errors on that framework). If invalidated, do **not** compare that framework
   to others in a strong claim.
4. Redact to **tool names and pass/fail** only — no tool args, hashes, contracts,
   or simulator state in report text.

### 2.2 H5 (mandatory extra steps)

1. Obtain Chloe's **per-run criterion annotations** before attributing H5 failures.
2. Apply `h5-scoring-rule-v1` aggregation logic when interpreting pass/fail —
   do not treat one criterion mismatch as full model failure without review.
3. Never copy criterion text or safer-alternative gold into case studies.

### 2.3 Repeat vs attempt (Lanfang recording)

- **Repeat logical run 1/2/3** = three planned observations (main + 2 targeted repeats).
- **Attempt 1/2** = tries within one logical run; attempt 2 only after **human
  reviewer** confirms infrastructure failure on attempt 1.
- Aggregates use the **latest eligible attempt** per logical run; your case study
  must state which attempt you analyzed.
- If attempt 2 looks like a score-motivated retry, mark row **ineligible** and
  exclude from findings (note in exclusion list).

### 2.4 Frozen representative IDs

| Task | Case ID |
|---|---|
| H1 | `H1-REVIEW-001` |
| H2 | `H2-REVIEW-001` |
| H4 | `H4-REVIEW-001` |
| H5 | `H5-REVIEW-001` |
| E1 | `E1-REVIEW-001` |
| E2 | `E2-REVIEW-001` |
| E3 | `E3-REVIEW-001` |
| E5 | `E5-001` (not `RETAIL-E5-001`) |

---

## 3. Lanfang pitfalls (avoid these)

| Pitfall | What to do instead |
|---|---|
| Analyzing v1.x or preflight rows | Cross-check `experiment_id` against v2.0 freeze record |
| Cherry-picking only dramatic failures | Include at least one **stable repeat** or null finding if data supports it |
| Cross-framework claims on invalidated E5 sweep | Check sweep validity before Finding 2-style claims |
| Calling timeout "model slowness" by default | Triage as `infrastructure` or `framework_adapter` first; cite progress markers if available |
| H5 attribution without annotations | Wait for Chloe; escalate `evaluator_or_gold` |
| Pasting full JSONL or ledger into draft | Reference `logical_run_id` locally only |
| Committing filled worksheet to Git | Keep local until redacted |
| Duplicating Mickey's skeleton | Send **delta** paragraphs only |
| Using stress rubric labels in pilot findings | Keep `stress_failure_rubric.md` out of standard accuracy narrative |
| Comparing frameworks run on different machines without note | Record env context in limitations if CrewAI/other ran off canonical host |

---

## 4. Case-study selection worksheet (Lanfang fills after A0–A2)

| Priority | Case ID | Framework | Repeat | Attempt | `logical_run_id` | Runtime symptom | Root cause (draft) | Eligible (Y/N) | Severity | Report |
|---:|---|---|---:|---:|---|---|---|---|---|---|
| 1 | `[TBD]` | | | | | | | | P0/P1 | yes |
| 2 | `[TBD]` | | | | | | | | P1 | yes |
| 3 | `[TBD]` | | | | | | | | P1 | yes |
| 4 | `[TBD]` | | | | | | | | P1/P2 | appendix |
| 5 | `[TBD]` | | | | | | | | P2 | appendix |
| 6 | `[TBD]` | | | | | stable repeat | n/a | | P2/none | limitations |

**Lanfang selection rules:**

- At least one **cross_framework_divergence** case if data supports it.
- At least one **repeat_inconsistency** on a representative case if observed.
- At least one **repeat-stable** representative case if observed (Finding 6).
- Skip P3 infrastructure-only rows in case-study body; list them in exclusion table.
- Do not select rows marked ineligible on attempt or sweep grounds.

---

## 5. Lanfang exclusion list (maintain locally)

| Case / run | Framework | Reason excluded | Source |
|---|---|---|---|
| `[TBD]` | | v1.x / preflight / invalid sweep / illegal retry / Chloe QA flag | |

Give Mickey a summary count only; do not commit raw ledger rows.

---

## 6. Draft — main findings (Lanfang placeholders)

> Replace `[TBD]` only with v2.0 scored rows. One narrow claim per finding.

1. **[Finding 1 — safety or policy, P0 if present]**
   On `[case_id]`, `[framework]` produced `[symptom]` while `[contrast]`.
   Root cause: `[category]`. Narrow claim: `[one sentence]`.

2. **[Finding 2 — cross-framework divergence, P1]**
   For `[case_id]`, `[framework X]` vs `[framework Y]` diverged under the same
   frozen config. Root cause: `[framework_adapter | model_formatting]`.
   **Only if both sweeps are valid.**

3. **[Finding 3 — repeat instability, P1]**
   Representative `[case_id]` on `[framework]` was `[inconsistent]` across
   repeats 1–3. Describe what varied at symptom layer.

4. **[Finding 4 — formatting vs capability, P1/P2]**
   On `[task_id]`, `[output_schema_invalid | instruction_drift]` occurred
   without content gold mismatch — symptom vs capability separated.

5. **[Finding 5 — evaluator boundary]**
   **Chloe written approval required before report inclusion.**
   Borderline `[task]` scoring at `[metric]` → `evaluator_or_gold`; no strong
   causal claim until resolved.

6. **[Finding 6 — repeat stability, optional but encouraged]**
   Representative `[case_id]` on `[framework]` was **consistent** across repeats
   1–3 at `[metric/symptom layer]`. Supports limitation: pilot stability under
   fixed protocol for that anchor case.

---

## 7. Draft — limitations and claim boundary (Lanfang → Mickey delta)

> Anchor all protocol claims to **`formal_benchmark_protocol_v2.0.md`** and the
> private v2.0 freeze record (experiment ID, commit SHA, timestamps). Do not
> cite v1.6 execution evidence as formal results.

### 7.1 Protocol limitations

This report summarizes a **controlled 60-case pilot** (228 logical runs in the
controlled-pilot phase, plus separate readiness preflights) across eight task
types and three agent frameworks. It is not a 400-case benchmark, a production
deployment study, or a stress-test suite. Task coverage is fixed by the frozen
`pilot-60-v1.0` manifest; results do not represent unseen task distributions.

Representative-case repeats measure **run-to-run stability** under fixed protocol
conditions, not statistical confidence intervals over a large case pool. Any
post-freeze change to cases, gold, evaluators, prompts, or runner code requires
a new protocol version and repeated affected preflights; such deviations must be
listed in the rerun ledger and excluded from unaffected aggregates.

All **v1.x and preliminary engineering smoke** runs are excluded from v2.0
readiness gates, denominators, and comparative claims.

### 7.2 Evaluator limitations

Metrics are **task-specific** by design; we do not report a composite score or
overall framework ranking. H5 uses owner-approved human criterion annotation
followed by deterministic aggregation. H4 gold uses programmatic extraction rules
that may disagree with reasonable alternative phrasing at field boundaries.

E5 pass requires **both** response-contract satisfaction and **final-state hash
equality** after independent replay. Evaluator borderline cases are escalated to
the evaluation owner rather than silently relabeled in WS5 analysis.

### 7.3 Provider and model limitations

All formal pilot runs use a single agent model configuration (`gpt-4o-mini`)
with temperature `0` under the frozen provider. Framework differences confound
orchestration with a **single model snapshot**; they do not establish superiority
across models or providers.

Timeout at the 300-second cap requires case-level attribution among model verbosity,
tool-loop depth, and infrastructure contention.

### 7.4 External-validity limitations

Healthcare and e-commerce tasks use synthetic or historical fixtures, not live
clinical or market decisions. Stress variants were **out of scope** for formal
delivery; incidental failures may appear as isolated case studies only.

---

## 8. Lanfang — failure taxonomy adjudication workflow

For each selected case:

1. Read evaluator-derived symptom (`failure_mode` from `adapter/evaluator.py` / metrics layer, or E5 failure class) from scored row.
2. For **E5**, apply `e5_gold_semantics_v0.3` precedence before generic taxonomy.
3. Assign one **root_cause_category** using `case_study_failure_taxonomy.md`
   precedence: `protocol_or_manifest` → `infrastructure` → `framework_adapter`
   → `evaluator_or_gold` → `model_formatting` → `model_capability`.
4. Add secondary tags (`cross_framework_divergence`, `repeat_inconsistency`, etc.).
5. Escalate `evaluator_or_gold` to Chloe and `framework_adapter` to Jessica
   **before** strong claims.
6. Record in `case_study_template.md`; do **not** publish aggregate symptom counts
   unless Chloe approves definitions for Mickey's tables.

Infrastructure (P3) stays in rerun ledger; never frame as model weakness.

---

## 9. Lanfang case-study shell (copy per case)

- **Experiment ID / commit:** `[v2.0 frozen values]`
- **Case ID / framework / repeat / attempt:** `[TBD]`
- **Symptom layer:** `[evaluator-derived failure_mode or E5 class]`
- **Root cause:** `[TBD]`
- **Eligible for aggregate:** `[Y/N + reason]`
- **Severity:** `[P0|P1|P2]`
- **Cross-framework / repeat notes:** `[TBD]`
- **Narrow claim / non-claim:** `[TBD]`
- **Owner review:** Chloe `[ ]` Jessica `[ ]`

Full template: `docs/case_study_template.md`

---

## 10. Lanfang checklist

- [ ] A0: Formal v2.0 scoring confirmed (228/228; H5 30/30)
- [ ] Pulled latest GitHub `main` protocol docs
- [ ] v2.0 exclusion list applied to every worksheet row
- [ ] Chloe failure candidates + scored outputs received
- [ ] E5 rows mapped through v0.3 semantics
- [ ] H5 rows have Chloe criterion annotations before attribution
- [ ] Worksheet includes attempt + eligible columns
- [ ] Findings include failure **and** stability (not cherry-picked only)
- [ ] Finding 5 only if Chloe approved in writing
- [ ] Xiaoxia confirmed any cited aggregate numbers
- [ ] Delivered skeleton **delta** to Mickey, not full report replacement
- [ ] No private gold, annotations, hashes, or raw JSONL in shared files
- [ ] Filled drafts kept local / gitignored

## 11. WS5 deliverables written (2026-08-18)

| Deliverable | Path | Status |
|---|---|---|
| Limitations (ready for Mickey) | `docs/ws5/limitations_deliverable.md` | Complete |
| Taxonomy adjudication summary | `docs/ws5/failure_taxonomy_adjudication_summary.md` | Complete |
| Main findings | `docs/ws5/main_findings_deliverable.md` | F1–F6 adjudicated; hold until C1–C6 |
| Exclusion list | `docs/ws5/exclusion_list.md` | Initial |
| Illustrative case study (excluded) | `docs/ws5/case_studies/CS-E3-001-openai-schema-format_EXCLUDED.md` | Format only |
| Package index | `docs/ws5/README.md` | Complete |
