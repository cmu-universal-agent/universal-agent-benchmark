# Stress Testing Docs — Quick Guide

Owner: Lanfang (hlf) · Branch: `lanfang/stress-testing-plan`

This folder’s stress-testing work is **documentation only** for now. It defines
how we will stress-test the eight core benchmark tasks before any live model
runs.

## What’s in this branch

| File | Purpose |
|---|---|
| `stress_testing_strategy.md` | Stress types, one-factor rule, variable control, test procedures |
| `eight_core_stress_matrix.md` | One primary stress scenario per task (H1–H5, E1–E3, E5) with pass/fail rules |
| `stress_failure_rubric.md` | Unified failure modes (`invalid_json`, `tool_failure`, etc.) |
| `schema_field_review.md` §10 | Proposed metadata fields for stress fixtures (pending Chloe) |

## How this connects to the codebase

```text
schemas/benchmark_case.schema.json   stress_type enum (8 values)
        │
        ▼
data/generated/core_pilot/cases/     base cases — do NOT edit for stress
        │
        ▼
tests/fixtures/stress_cases/         stress variants (planned, not created yet)
        │
        ▼
scripts/run_benchmark.py             runs tasks through 3 framework adapters
adapter/evaluator.py                 structural failure_mode checks
evaluator_data/gold_answers/         evaluator-only gold (never in agent prompt)
```

**Rule:** Each stress variant changes **one factor** and is stored separately.
Core pilot JSON stays unchanged.

## Eight tasks at a glance

| ID | Vertical | Task | Primary stress |
|---|---|---|---|
| H1 | healthcare | Evidence QA (PubMedQA) | `conflicting_evidence` |
| H2 | healthcare | Symptom triage (HealthBench) | `ambiguous_input` |
| H4 | healthcare | Clinical note summary (ACI-Bench) | `long_context` |
| H5 | healthcare | Refusal / boundaries (MedSafetyBench) | `policy_or_safety_trap` |
| E1 | ecommerce | Product trend research | `conflicting_evidence` |
| E2 | ecommerce | Product recommendation | `missing_information` |
| E3 | ecommerce | Return/refund policy (tau2-bench) | `policy_or_safety_trap` |
| E5 | ecommerce | Customer support tool use (tau2-bench) | `tool_failure` |

## Running the project (when env is ready)

Requirements: **Python 3.10+**, three venvs, `.env` with API key.

```bash
cp .env.example .env
./scripts/setup_envs.sh

# Offline checks (no model calls)
.venv-openai/bin/python scripts/validate_tasks.py
.venv-openai/bin/python scripts/validate_contract_fixtures.py

# Live smoke (needs API key)
./scripts/run_smoke_tests.sh
```

Stress fixtures and evaluator wiring come **after** Chloe confirms schema
fields in `schema_field_review.md` §10.

## Related project docs

- `PROJECT_LEAD_GUIDE.md` — current status, owners, gates
- `core_pilot_data_preparation.md` — how the 64 core pilot cases are built
- `framework_comparison_rationale.md` — why and how we compare frameworks
