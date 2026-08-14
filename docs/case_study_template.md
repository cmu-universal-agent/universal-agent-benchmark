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
| Evaluator-derived `failure_mode` | |
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
additional targeted repeats. Record one row per attempt so a permitted retry
does not erase attempt `1`. Attempt `2` is reserved for one documented,
manually confirmed infrastructure retry and is never used to replace a poor
result.

| Repeat | Logical run ID | Attempt | Status | Rerun reason | Result run ID | Outcome | Included in analysis? |
|---:|---|---:|---|---|---|---|---|
| 1 | | 1 | | | | | |
| 1 | | 2 (if allowed) | | | | | |
| 2 | | 1 | | | | | |
| 2 | | 2 (if allowed) | | | | | |
| 3 | | 1 | | | | | |
| 3 | | 2 (if allowed) | | | | | |

**Repeat inconsistency?** yes / no — if yes, describe what varied.

### Run/result field mapping

| Field | Current source |
|---|---|
| `case_id`, `task_id`, `framework`, `experiment_id`, result run ID | Result JSONL; result run ID is `run_id` |
| `logical_run_id`, `repeat`, `attempt`, `status`, `rerun_reason` | Attempt ledger |

Automatic joining is **pending**. The current result JSONL lacks
`logical_run_id` and `attempt`, while the attempt ledger lacks the corresponding
result `run_id`. Suitability reporting and dashboard grouping also do not yet
preserve repeats/attempts. Until a follow-up runner/report integration change
adds an unambiguous join key and repeat-safe grouping, record both references
manually and do not claim automated run-matrix completeness.

The runner currently enforces a non-empty rerun reason and at most two
attempts; it does not validate the prior failure class. Before attempt `2`, a
human reviewer must confirm that attempt `1` was an eligible infrastructure
failure. Include only the final eligible attempt in aggregate analysis while
retaining every attempt for audit.

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
