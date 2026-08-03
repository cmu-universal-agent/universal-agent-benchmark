# Representative Case IDs (Draft for Chloe Review)

Status: **Draft — pending owner approval**
Owner: Lanfang Hai
Prepared: 2026-08-04
Generator: `scripts/prepare_core_pilot.py` at `core-pilot-converter-v9`, seed `42`

## Purpose

Select **one representative case per task type** for the 48 targeted-repeat runs
(8 cases × 3 frameworks × 2 extra repeats). The first run for each case is
already included in the 180-run main experiment; repeats measure stability on
cases that exercise core task semantics and likely failure modes.

Per the delivery plan, Chloe must approve the final eight IDs before they are
frozen in the experiment manifest.

## Selection rules

1. Use cases from the frozen 60-case pilot manifest (`data/generated/core_pilot/`).
2. Prefer **owner-reviewed or hard-difficulty** slots when they cover the task's
   primary evaluation axis.
3. Cover **diverse gold/decision types** within each task where the manifest
   allows (for example H2 urgency bands, E3 policy outcomes).
4. Do **not** use public synthetic fixtures (for example `RETAIL-E5-001`) as
   formal representatives.
5. If the manifest changes after freeze, regenerate this list and re-approve.

## Proposed eight IDs

| Task | Proposed case ID | Difficulty | Why this case |
|---|---|---|---|
| H1 | `H1-REVIEW-001` | easy | Baseline PubMedQA evidence QA; short context; tests structured yes/no/maybe output and citation grounding. Source: PubMed `23222920`. |
| H2 | `H2-REVIEW-003` | hard | Non-emergency HealthBench triage classified as **urgent** under v2 timeframe rules; exercises urgency rubric and safety escalation wording. |
| H4 | `H4-REVIEW-007` | hard | **Owner-approved** extraction case (Chloe sign-off 2026-07-21); includes active-medication history (`currently taking metformin`) and multi-field extraction stress. Source: ACI-Bench `D2N082`. |
| H5 | `H5-REVIEW-001` | hard | MedSafetyBench refusal boundary (`refuse_only`). **Provisional:** swap to a Chloe owner-authored **escalate** case once `evaluator_data/local_review_decisions/h5_owner_cases/` is present in the canonical checkout. |
| E1 | `E1-REVIEW-002` | medium | **Decreasing** historical review trend; not the easiest E1 bucket; tests trend_direction and evidence synthesis from fixed yearly tables. |
| E2 | `E2-REVIEW-001` | medium | Fixed candidate snapshot recommendation task; tests ranked recommendations and `constraints_satisfied`. |
| E3 | `E3-REVIEW-003` | hard | **needs_review** policy outcome on tau retail; multi-action scenario; tests policy judgment under ambiguity. Source task `10`. |
| E5 | `TBD` | — | Requires `evaluator_data/local_review_decisions/E5_cases_batch1.json` (gitignored). Request the **first owner-approved batch-1 case_id** from Jessica/Chloe. Do not substitute `RETAIL-E5-001`. |

## Local generation status (2026-08-04)

| Item | Status |
|---|---|
| GitHub `main` | Synced to `842566d` (PR #24) |
| Source dataset caches | Validated (`CORE_DATASET_CACHES_OK`) |
| Generated cases (local) | 56 / 60 — missing E5 batch |
| `validate_core_pilot.py` | Fails until E5 batch is added |
| H5 owner-authored cases | Not present locally — current H5 set is source-derived refusal only |

Commands used:

```bash
.venv-openai/bin/python scripts/validate_core_dataset_caches.py
.venv-openai/bin/python scripts/prepare_core_pilot.py --tasks H1 H2 H4 H5 E1 E2 E3 --per-task 8 --overwrite
.venv-openai/bin/python scripts/run_benchmark.py --task data/generated/core_pilot/cases --list-only
```

After Jessica supplies E5 batch-1 and H5 owner cases on the canonical machine:

```bash
.venv-openai/bin/python scripts/prepare_core_pilot.py --per-task 8 --overwrite
.venv-openai/bin/python scripts/validate_core_pilot.py --expected-per-task 8
```

Then confirm E5 and (if needed) H5 rows in the table above against the final
manifest before Chloe approval.

## Approval record

| Reviewer | Decision | Date | Notes |
|---|---|---|---|
| Chloe | pending | | |
| Jessica | pending | | Confirm manifest SHA-256 at freeze |
| Mickey | pending | | Lock into 252-run matrix |

## Handoff

- **To Jessica / Chloe:** this draft list + manifest hash after full 60-case generation.
- **From Chloe:** approved eight IDs for `docs/experiment_report_skeleton.md` § Targeted repeats.
- **To Mickey:** approved IDs for run tracking and report skeleton.
