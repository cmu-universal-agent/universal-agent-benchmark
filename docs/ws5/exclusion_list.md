# WS5 Exclusion List — Lanfang (maintain locally)

Status: **Initial exclusions documented; v2.0 rows pending**
Owner: Lanfang Hai
Prepared: 2026-08-18

Give Mickey **summary counts only**. Do not commit raw JSONL or ledger excerpts.

---

## Permanent exclusions (never enter v2.0 failure analysis)

| Source | Reason | Approx. scale |
|---|---|---|
| `prelim-tech-smoke-20260717-*` | `technical_smoke_only`; pre-v2.0 engineering smoke | 42 calls |
| All v1.x candidate readiness attempts | Excluded by `formal_benchmark_protocol_v2.0.md` | See private freeze record |
| Readiness preflights under preflight-only experiment ID | Not controlled-pilot results | 24 logical runs |
| Stress-test variants | Out of formal delivery scope | N/A |
| Public synthetic `RETAIL-E5-001` | Not formal case `E5-001` | N/A |

Reference: `results/preliminary_technical_smoke_20260717.md` (local engineering
record only).

---

## Conditional exclusions (apply per row when triaging v2.0)

| Condition | Lanfang action |
|---|---|
| Wrong `experiment_id` vs v2.0 freeze | Mark ineligible; do not analyze |
| Attempt 2 without infrastructure eligibility review | Mark ineligible |
| E5 framework sweep invalidated (>5% final-attempt errors) | Exclude framework from strong comparative claims |
| Chloe QA flag on row | Exclude until resolved |
| Preflight or list-only discovery run | Exclude |

---

## v2.0 controlled-pilot rows (pending)

| Case / logical run | Framework | Repeat | Attempt | Eligible | Notes |
|---|---|---:|---:|---:|---|
| `[awaiting Chloe package]` | | | | | |

**Target denominator for WS5 case studies:** subset of 228 controlled-pilot logical
runs on v2.0 formal experiment ID, minus rows above.

---

## Illustrative case study excluded from report

| File | Reason |
|---|---|
| `case_studies/CS-E3-001-openai-schema-format_EXCLUDED.md` | Derived from July 2026 technical smoke only; shows WS5 format, not v2.0 evidence |
