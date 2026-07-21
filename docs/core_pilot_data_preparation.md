# Core Pilot Data Preparation

This workflow prepares local review samples for the eight minimum benchmark
tasks: H1, H2, H4, H5, E1, E2, E3, and E5. Raw datasets and generated samples
stay under the gitignored `data/` directory.

## Source caches

| Tasks | Source | Local cache |
|---|---|---|
| H1 | [PubMedQA](https://github.com/pubmedqa/pubmedqa) | `data/pubmedqa/ori_pqal.json` |
| H2 | [HealthBench main JSONL](https://openaipublic.blob.core.windows.net/simple-evals/healthbench/2025-05-07-06-14-12_oss_eval.jsonl) | `data/healthbench/2025-05-07-06-14-12_oss_eval.jsonl` |
| H4 | [ACI-Bench](https://github.com/wyim/aci-bench) | `data/vendor/aci-bench/` |
| H5 | [MedSafetyBench](https://github.com/AI4LIFE-GROUP/med-safety-bench) | `data/vendor/med-safety-bench/` |
| E1, E2 | [Amazon Reviews 2023](https://cseweb.ucsd.edu/~jmcauley/datasets.html) (`Subscription_Boxes`) | `data/amazon_reviews_2023/` |
| E3, E5 | [tau2-bench retail](https://github.com/sierra-research/tau2-bench) | `data/vendor/tau2-retail/` |

MIMIC-IV-ED is not downloaded because it requires PhysioNet credentials and a
data-use agreement. Retailrocket is not needed for this first fixed E2 pilot.

## Validate and generate

From the repository root, using an environment that has `jsonschema`:

```powershell
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_core_dataset_caches.py"
& ".\.venv-openai\Scripts\python.exe" -m unittest tests.test_core_pilot_extraction -v
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_dataset_specs.py"
& ".\.venv-openai\Scripts\python.exe" ".\scripts\prepare_core_pilot.py" --per-task 8 --overwrite
& ".\.venv-openai\Scripts\python.exe" ".\scripts\validate_core_pilot.py" --expected-per-task 8
& ".\.venv-openai\Scripts\python.exe" ".\scripts\run_benchmark.py" --task ".\data\generated\core_pilot\cases" --list-only
```

Generated files are written to `data/generated/core_pilot/`:

- `cases/`: agent-visible Benchmark Case Schema v1.0 JSON;
- `gold/`: evaluator-only JSONL, never used to construct an agent prompt;
- `split_manifest.json`: deterministic source IDs and split assignments;
- `coverage_report.json`: source coverage, exclusions, and remaining gaps.

## Review boundaries

- H2 emergency and uncertain come directly from native physician-agreed tags.
  Urgent, routine, and self-care use Chloe's v2 criterion-scoped timeframe rule.
  H2-003/004/005/008 now have local evaluator-only owner decisions; 004 remains
  `routine`. Urgency-label review and H2 gold generation are complete. Chloe
  gave no threshold-adjustment recommendation; the current hard-skewed
  difficulty rule is retained provisionally and will be calibrated later.
- H4 fields are programmatically extracted from the reference clinical note.
  The v3 rules include secondary history-header stripping, honorific-safe
  sentence splitting, retention of short same-line clinical statements,
  always-on HPI symptom supplementation, and infection/lingering-cold symptom
  coverage. Empty/unmatched areas are flagged rather than invented. The eight
  regenerated outputs still require Chloe's owner review.
- H5 locally includes Chloe's four owner-authored cases (two `clarify`, two
  `escalate`) and fills the remaining review slots with source-derived refusal
  samples. Chloe approved all four owner-authored cases/rubrics on 2026-07-21.
  Exact prompts/gold/rubrics remain gitignored and evaluator-only.
- E3 excludes every scenario containing `cancel_pending_order`, including
  mixed-action scenarios. Chloe confirmed on 2026-07-20 that this action must
  not map to `refund_allowed` because it is outside E3's delivered-order policy
  judgment scope.
- E5 cases and expected actions are ready, but live execution requires one
  shared tau retail simulator/tool bridge exposed identically to all three
  framework adapters.
