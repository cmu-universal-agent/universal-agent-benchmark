# Representative Case IDs

Status: **Frozen — owner approved**
Owner: Lanfang Hai
Prepared: 2026-08-04
Approved by: Chloe
Approved: 2026-08-10
Generator: `scripts/prepare_core_pilot.py` at `core-pilot-converter-v9`, seed `42`

## Purpose

Select **one representative case per task type** for the 48 targeted-repeat runs
(8 cases × 3 frameworks × 2 additional logical runs). The first observation for
each case is already included in the 180-run main pilot; the two additional
logical runs produce three observations per framework and representative case.

## Frozen eight IDs

| Task | Representative case ID | Approval |
|---|---|---|
| H1 | `H1-REVIEW-001` | Chloe approved, 2026-08-10 |
| H2 | `H2-REVIEW-001` | Chloe approved, 2026-08-10 |
| H4 | `H4-REVIEW-001` | Chloe approved, 2026-08-10 |
| H5 | `H5-REVIEW-001` | Chloe approved, 2026-08-10; `REVIEW` disambiguates the selected H5 family |
| E1 | `E1-REVIEW-001` | Chloe approved, 2026-08-10 |
| E2 | `E2-REVIEW-001` | Chloe approved, 2026-08-10 |
| E3 | `E3-REVIEW-001` | Chloe approved, 2026-08-10 |
| E5 | `E5-001` | Chloe approved, 2026-08-10; not the public synthetic `RETAIL-E5-001` fixture |

## Freeze evidence

| Item | Status |
|---|---|
| GitHub `main` at freeze | `842566d` (PR #24) |
| Controlled-pilot manifest | Frozen at 60 / 60 cases |
| Evaluator-only gold approval | 60 / 60 owner approved |
| Representative IDs | 8 / 8 owner approved |
| Core-pilot validation | Passed with 60 cases, 60 gold records, and zero leakage |

The manifest, evaluator-only gold, approval evidence, hashes, raw results, and
traces remain local-only and are not repository deliverables. After freeze,
any change to a representative ID requires a new version, a recorded reason,
owner approval, and revalidation of the affected preflight/repeat plan.

## Run-recording rule

- A representative case has three distinct logical runs per framework: the
  main-pilot run plus two additional targeted repeats.
- Each logical run starts at attempt `1`.
- Attempt `2` is permitted only for one documented infrastructure retry under
  the frozen rerun policy.
- A poor answer, score, or tool choice is not retry-eligible.

## Approval record

| Reviewer | Decision | Date | Notes |
|---|---|---|---|
| Chloe | approved | 2026-08-10 | Approved the eight `001` representative cases |
| Jessica | verified | 2026-08-10 | Verified IDs against the frozen local manifest and owner record |
| Mickey | pending integration | | Add the frozen IDs to report/run tracking without changing them |

## Handoff

- **To Jessica:** use exactly these eight IDs for the two additional targeted
  repeats per framework.
- **To Chloe:** score and QA the resulting logical runs against local-only gold.
- **To Mickey:** use these frozen IDs in the report and run matrix.
