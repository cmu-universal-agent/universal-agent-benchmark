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
  Urgent, routine, and self-care use the owner-provided rubric keyword rule and
  remain review samples until spot-checked.
- H4 fields are programmatically extracted from the reference clinical note.
  Empty/unmatched areas are flagged rather than invented.
- H5 currently generates source-derived refusal samples only. Chloe-owned
  clarify/escalate cases and their rubric are still required.
- E3 excludes `cancel_pending_order -> refund_allowed`; that cross-schema
  semantic requires owner confirmation.
- E5 cases and expected actions are ready, but live execution requires one
  shared tau retail simulator/tool bridge exposed identically to all three
  framework adapters.
