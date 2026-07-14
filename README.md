# Universal Agent Benchmark

Compares LangGraph, CrewAI, and OpenAI Agents SDK across two verticals — medical diagnostic QA and e-commerce trend research — through a shared adapter interface (`adapter/`).

## Setup

```bash
cp .env.example .env          # ! fill in your API key, base URL, model
./scripts/setup_envs.sh       # creates .venv-openai, .venv-langgraph, .venv-crewai
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

## Verticals

Both verticals are built from real public data (not fabricated text), with ground truth kept in each task's `metadata` for scoring. Regenerating is self-cleaning (stale task files are removed first) and reproducible (`--seed`, default 42).

**Medical diagnostic** — 10 tasks in `verticals/medical_diagnostic/`, sampled from [PubMedQA](https://github.com/pubmedqa/pubmedqa)'s expert-labeled split (biomedical research-literature QA, not patient data).

```bash
python3 scripts/prepare_medical_tasks.py
```

**E-commerce trend research** — 10 tasks in `verticals/ecommerce_trend_research/`, sampled from the Subscription_Boxes category of [Amazon Reviews 2023](https://cseweb.ucsd.edu/~jmcauley/datasets.html) (McAuley Lab, UCSD). Each task gives a product's real yearly review-count and rating history.

```bash
python3 scripts/prepare_ecommerce_tasks.py
```

Every task's prompt already contains everything needed to answer, but a mock tool (`tools.py` in each vertical directory, backed only by the local data cache) is also available to the agent. Since the tasks never require it, any call is measurable tool overuse — tracked as `tool_call_count` on `AgentRunResult`.

## Analysis

```bash
python3 scripts/report_hallucination_risk.py    # confidently-wrong answers vs. ground truth
python3 scripts/report_medical_safety.py        # safety disclaimer / risky language / escalation checks
python3 scripts/generate_suitability_matrix.py  # writes results/framework_suitability_matrix.md
python3 scripts/test_tool_failure.py --framework <name>  # run once per venv; simulates a failing tool
```

`generate_suitability_matrix.py` is the final deliverable: per-vertical accuracy, latency, and failure-mode tables with ASCII bar charts, plus qualitative findings and a recommendation per framework.
