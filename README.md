# Universal Agent Benchmark

For the current implementation status, proposal/workplan index, ownership,
decision gates, and session-resume workflow, start with
`docs/PROJECT_LEAD_GUIDE.md`. The older
`docs/current_status_and_handoff.md` remains a historical WS2 handoff snapshot.

Compares LangGraph, CrewAI, and OpenAI Agents SDK across two verticals — medical diagnostic QA and e-commerce trend research — through a shared adapter interface (`adapter/`).

## Setup

```bash
cp .env.example .env          # ! fill in your API key, base URL, model
./scripts/setup_envs.sh       # creates .venv-openai, .venv-langgraph, .venv-crewai
```

On Windows PowerShell:

```powershell
.\scripts\setup_envs.ps1
```

Never commit `.env`.

## Quick start

Run the full sweep (all verticals, all frameworks) plus every analysis report in one command:

```bash
./scripts/run_all.sh
```

Ends with `results/framework_suitability_matrix.md` — the final deliverable. See below to run any piece individually.

## Running steps by steps

Smoke test all three frameworks individually:

```bash
./scripts/run_smoke_tests.sh
```

On Windows PowerShell:

```powershell
.\scripts\run_smoke_tests.ps1
```

Or run one framework directly:

```bash
source .venv-openai/bin/activate && python frameworks/openai_agents_sdk/run.py && deactivate
source .venv-langgraph/bin/activate && python frameworks/langgraph_agent/run.py && deactivate
source .venv-crewai/bin/activate && python frameworks/crewai_agent/run.py && deactivate
```

Run the shared benchmark across all three frameworks:

```bash
python3 scripts/run_benchmark.py                                      # smoke test (default)
python3 scripts/run_benchmark.py --task verticals/medical_diagnostic/ # sweep a whole vertical
python3 scripts/run_benchmark.py --task <dir> --repeats 3             # N runs per (task, framework)
```

Each result is appended to `results/metrics/<vertical>_results.jsonl` as a standardized `AgentRunResult`. Every run ends with a "Failure Modes" breakdown (`ok`, `instruction_drift`, `missing_required_keys`, `invalid_json`, `tool_overuse`, `runtime_exception:<type>`) from `adapter/evaluator.py`.

Every new result records the model and framework at execution time, including
`run_id`, `experiment_id`, `framework_version`, `model_provider`, `model_name`,
generation settings, timestamps, raw output, and normalized tool-call traces.
Legacy rows without `model_name` are treated as `unknown` and must not be mixed
with model-controlled comparisons.

To override the model for one complete benchmark session and give the session a
stable experiment ID:

```bash
python3 scripts/run_benchmark.py \
  --task verticals/medical_diagnostic/ \
  --model gpt-4o-mini \
  --experiment-id pilot-medical-gpt4omini-v1
```

## Task format compatibility

The shared task loader accepts both the current legacy task files
(`task_id`, `vertical`, `prompt`, `metadata`) and Benchmark Case Schema v1.0
files. This lets the existing pilot continue while the final v1.0 field review
is pending. A v1.0 task's structured `input` is rendered into a deterministic
prompt, and its `allowed_tools` list is enforced by every framework adapter.

Validate all task files without calling a model:

```powershell
.\.venv-crewai\Scripts\python.exe scripts\validate_tasks.py
```

Legacy-compatible files are reported as `LEGACY`. After migration, add
`--require-v1` to make any remaining legacy file fail validation.

## Verticals

Both verticals are built from real public data (not fabricated text). Existing
task files are never replaced unless `--overwrite` is passed explicitly.
Sampling is reproducible (`--seed`, default 42).

**Medical diagnostic** — 10 tasks in `verticals/medical_diagnostic/`, sampled from [PubMedQA](https://github.com/pubmedqa/pubmedqa)'s expert-labeled split (biomedical research-literature QA, not patient data).

```bash
python3 scripts/prepare_medical_tasks.py --cache-only  # download cache, keep tasks
python3 scripts/prepare_medical_tasks.py --overwrite   # explicitly rebuild tasks
```

**E-commerce trend research** — 10 tasks in `verticals/ecommerce_trend_research/`, sampled from the Subscription_Boxes category of [Amazon Reviews 2023](https://cseweb.ucsd.edu/~jmcauley/datasets.html) (McAuley Lab, UCSD). Each task gives a product's real yearly review-count and rating history.

```bash
python3 scripts/prepare_ecommerce_tasks.py --cache-only  # download caches, keep tasks
python3 scripts/prepare_ecommerce_tasks.py --overwrite   # explicitly rebuild tasks
```

Every task's prompt already contains everything needed to answer, but a mock tool (`tools.py` in each vertical directory, backed only by the local data cache) is also available to the agent. Since the tasks never require it, any call is measurable tool overuse — tracked as `tool_call_count` on `AgentRunResult`.

## Analysis

```bash
python3 scripts/report_hallucination_risk.py    # confidently-wrong answers vs. ground truth
python3 scripts/report_medical_safety.py        # safety disclaimer / risky language / escalation checks
python3 scripts/generate_suitability_matrix.py  # writes results/framework_suitability_matrix.md
python3 scripts/test_tool_failure.py --framework <name>  # run once per venv; simulates a failing tool
python3 scripts/test_tool_success.py --framework <name>  # run once per venv; records a successful tool trace
python3 scripts/check_result_fields.py                   # no API calls; audits recorded field coverage
python3 scripts/validate_contract_fixtures.py            # no API calls; validates valid/invalid schema fixtures
python3 scripts/validate_adapter_contracts.py            # no API calls; checks legacy/v1 and normalized tool logs
python3 scripts/validate_shared_tool_contracts.py        # no API calls; checks no-tool/success/failure traces
python3 scripts/validate_dataset_specs.py                 # no API calls; checks draft H2/H4 spec consistency
```

The existing smoke test covers the no-tool scenario. Together, the smoke test,
`test_tool_success.py`, and `test_tool_failure.py` provide the three initial
adapter-contract scenarios: no tool, successful tool call, and failing tool.

`generate_suitability_matrix.py` is the final deliverable: per-vertical accuracy, latency, and failure-mode tables with ASCII bar charts, plus qualitative findings and a recommendation per framework.

## Retail run console (dashboard)

```bash
python3 scripts/generate_dashboard.py --vertical retail   # writes results/dashboard.html
open results/dashboard.html                                # macOS; or just double-click the file
```

Reads the latest row per `(task_id, framework, experiment_label)` from `results/metrics/retail_results.jsonl` and renders a self-contained, read-only HTML page — no server, nothing to deploy. The public view is explicitly synthetic technical validation, not benchmark scoring: it publishes sanitized trace summaries and aggregate final-state verdicts only. `results/dashboard.html` is generated (gitignored), so it isn't checked in or viewable on GitHub — regenerate it locally and open the file to view it.
