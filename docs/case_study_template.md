# Case Study Template

Status: **Draft — fill one file per selected failure or repeat-divergence case**
Owner: Lanfang Hai
Prepared: 2026-08-04

Copy this template for each case study. Store working drafts outside Git if they
quote evaluator-only gold; publish only redacted, owner-approved excerpts in the
final report.

---

## Case study metadata

| Field | Value |
|---|---|
| Case ID | |
| Task ID | H1 / H2 / H4 / H5 / E1 / E2 / E3 / E5 |
| Representative case? | yes / no |
| Framework | openai_agents_sdk / langgraph / crewai |
| Experiment ID | |
| Logical run ID | |
| Repeat logical run | 1 / 2 / 3 |
| Attempt number | 1 / 2 |
| Model (frozen config) | |
| Formal experiment commit | |
| Include in report? | yes / appendix / no |

---

## 1. Task summary (agent-visible only)

**Instruction (1–2 sentences):**

**Why this case was selected:**

**Allowed tools:**

**Expected output shape (no gold values):**

---

## 2. Run outcome

| Field | Value |
|---|---|
| Runtime `failure_mode` | |
| Evaluator pass/fail | |
| Primary metric(s) | |
| Tool call count | |
| Latency / token budget hit? | |

**Final output excerpt (redacted, ≤ 120 words):**

**Tool trace summary (ordered list of tool names + pass/fail):**

---

## 3. Failure classification

Use `docs/case_study_failure_taxonomy.md`.

| Field | Value |
|---|---|
| Primary root cause | model_capability / model_formatting / framework_adapter / evaluator_or_gold / infrastructure / protocol_or_manifest |
| Severity | P0 / P1 / P2 / P3 |
| Secondary tags | |
| Contributing factors | |

**One-sentence diagnosis:**

---

## 4. Comparison evidence

### Cross-framework (same case, same model)

| Framework | Outcome | Notes |
|---|---|---|
| OpenAI Agents SDK | | |
| LangGraph | | |
| CrewAI | | |

### Targeted repeats (if representative case)

The three observations are distinct logical runs: the main-pilot run plus two
additional targeted repeats. Each logical run starts at attempt `1`; attempt
`2` is reserved for one documented infrastructure retry and is never used to
replace a poor result.

| Repeat logical run | Logical run ID | Attempt (1 / 2) | Outcome | Consistent? |
|---:|---|---:|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

**Repeat inconsistency?** yes / no — if yes, describe what varied.

---

## 5. Root-cause narrative

### What happened

(3–5 sentences, past tense, evidence-based.)

### Why it is not a different category

| Ruled out | Reason |
|---|---|
| Infrastructure | |
| Framework adapter | |
| Evaluator/gold | |
| Model formatting | |

### Framework-specific notes (if applicable)

---

## 6. Illustrative excerpt

**Prompt fragment or tool argument (redacted):**

**Agent turn or tool result (redacted):**

**Evaluator check that failed (name only, no gold leak):**

---

## 7. Limitations and claim boundary

- What this case **does** support (narrow claim):
- What this case **does not** support:
- Generalization risk:

---

## 8. Owner review

| Reviewer | Role | Status | Date | Notes |
|---|---|---|---|---|
| Lanfang | Author | draft | | |
| Chloe | Evaluator/gold | pending | | Required if `evaluator_or_gold` |
| Jessica | Framework/integration | pending | | Required if `framework_adapter` |
| Mickey | Report editor | pending | | |

---

## 9. Artifacts

| Artifact | Path or ID |
|---|---|
| Result row reference | Local-only path or run ID; do not commit raw output |
| Attempt ledger entry | Local-only ledger reference |
| Trace / run log | Local-only reference; do not commit raw trace |
| Screenshot (if dashboard) | |

---

## Checklist before submission

- [ ] No evaluator-only gold, rubric criteria, per-run H5 criterion annotations,
      or private E5 hashes in text.
- [ ] Raw outputs, attempt ledgers, and traces remain local-only.
- [ ] Root cause uses taxonomy precedence.
- [ ] Infrastructure failures marked P3 unless reporting rerun policy.
- [ ] Cross-framework table filled or marked N/A with reason.
- [ ] Claim boundary section completed.
- [ ] Referenced case ID matches frozen manifest SHA.
