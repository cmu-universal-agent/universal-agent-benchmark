# Case Study — E3-REVIEW-001 / OpenAI Agents SDK (EXCLUDED ILLUSTRATION)

> **NOT FOR v2.0 REPORT.** This case study demonstrates Lanfang's WS5 format only.
> Source: `results/preliminary_technical_smoke_20260717.md` (`technical_smoke_only`).
> Excluded by `docs/ws5/exclusion_list.md`. Do not cite in formal findings.

---

## Case study metadata

| Field | Value |
|---|---|
| Case ID | `E3-REVIEW-001` |
| Task ID | E3 |
| Representative case? | yes (anchor ID; this row is not v2.0 data) |
| Framework | openai_agents_sdk |
| Experiment ID | `prelim-tech-smoke-20260717-boolean-fix` (**excluded**) |
| Logical run ID | `[not recorded in smoke]` |
| Repeat logical run | 1 |
| Attempt number | 1 |
| Model (frozen config) | gpt-4o-mini, temperature 0 |
| Formal experiment commit | `d258ec2` era (**excluded from v2.0**) |
| Include in report? | **no — template only** |

---

## 1. Task summary (agent-visible only)

**Instruction:** Delivered-order return/refund policy judgment on a fixed customer
scenario snapshot; return structured JSON with policy decision and rationale fields
at defined top-level keys.

**Why this case was selected (illustration):** Shows **symptom vs formatting**
separation after runner schema validation landed; useful for adjudication training
only.

**Allowed tools:** None required for this smoke fixture (evidence embedded in prompt).

**Expected output shape:** Single JSON object with task-appropriate top-level fields
including policy decision; required non-nested fields must not be buried inside
`result` only.

---

## 2. Run outcome

| Field | Value |
|---|---|
| Runtime `failure_mode` | `output_schema_invalid` |
| Evaluator pass/fail | Fail strict schema (smoke check; not formal E3 gold score) |
| Primary metric(s) | `output_schema_valid_rate = 0%` for this row |
| Tool call count | 0 |
| Latency / token budget hit? | No |

**Final output excerpt (redacted, structural issue only):**

The model returned parseable JSON with correct case/task identity, but placed
`explanation` and `evidence_ids` **inside** `result` instead of at the required
top-level keys.

**Tool trace summary:** None.

---

## 3. Failure classification

| Field | Value |
|---|---|
| Primary root cause | `model_formatting` |
| Severity | P2 (illustrative; would be appendix in a formal pilot) |
| Secondary tags | `instruction_drift` |
| Contributing factors | OpenAI Agents SDK plain-text JSON generation without structured-output enforcement at smoke time |

**One-sentence diagnosis:** The adapter run succeeded at JSON parsing, but the
model violated the task output shape, and the updated runner correctly surfaced
`output_schema_invalid` instead of silently scoring `ok`.

---

## 4. Comparison evidence

### Cross-framework (same case, same smoke)

| Framework | Outcome | Notes |
|---|---|---|
| OpenAI Agents SDK | `output_schema_invalid` | Nested fields inside `result` |
| LangGraph | Strict schema pass | Smoke row |
| CrewAI | Strict schema pass | Smoke row |

### Targeted repeats

N/A — smoke used one repeat only; excluded from repeat-stability claims.

---

## 5. Root-cause narrative

### What happened

On the after-fix technical smoke, OpenAI Agents SDK produced valid JSON with correct
case identity but incorrect field placement for E3. LangGraph and CrewAI passed strict
schema on the same case. The runner reported the OpenAI row as schema-invalid, which
would have been missed before schema validation integration.

### Why it is not a different category

| Ruled out | Reason |
|---|---|
| Infrastructure | Run completed; JSON parse succeeded |
| Framework adapter | Identity checks passed; issue is output shape from model path |
| Evaluator/gold | Smoke strict-schema check only; no formal E3 policy gold claim here |
| Model capability (content) | Policy decision semantics not adjudicated in this smoke |

---

## 6. Limitations and claim boundary (this illustration)

- Does **not** prove OpenAI Agents SDK is worse on E3 in the v2.0 pilot.
- Does **not** establish policy-decision correctness (`return_allowed` vs alternatives).
- Supports only the engineering lesson: **JSON validity ≠ task schema validity**.

---

## 7. Owner review

| Reviewer | Status | Notes |
|---|---|---|
| Lanfang | template draft | Excluded from v2.0 report |
| Chloe | n/a | Illustration only |
| Jessica | n/a | Illustration only |
| Mickey | n/a | Format reference only |
