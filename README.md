# Universal Agent Benchmark

Compare **LangGraph**, **CrewAI**, and **OpenAI Agents SDK** on the same tasks,
model, and output contract across the healthcare and ecommerce benchmark
verticals, plus a stateful **retail WS3 integration slice**. The benchmark asks
**where each framework breaks**, while WS3 separately validates whether real
framework wrappers can expose the same canonical tools, traces, and final
state. All adapters share `adapter/` for task loading, result shape,
evaluation, and JSONL logging so differences come from framework behavior, not
from incompatible prompts or schemas.

**Requirements:** Python **3.10+** (code uses `str | None` union syntax), network
access for setup and model calls, and an OpenAI-compatible API key in `.env`.

---

## 1. Background

| Dimension | Healthcare vertical | E-commerce vertical |
|---|---|---|
| Committed tasks | `verticals/medical_diagnostic/` — 10 PubMedQA literature-QA cases | `verticals/ecommerce_trend_research/` — 10 Amazon Reviews 2023 trend cases |
| Pilot scope (local) | Eight task types: H1, H2, H4, H5 | E1, E2, E3, E5 — generated under `data/generated/core_pilot/` (not in Git) |
| Stress axis | Evidence, triage, summarization, refusal | Trend synthesis, recommendations, policy, multi-step tools |

The repository ships **legacy task JSON** for a 20-case regression sweep (mostly
H1/E1-shaped). The **eight-task core pilot** (64 review cases) is built locally
from public datasets; see [Data preparation](#stage-2-data-preparation). Preliminary
runs in `results/` are **engineering smoke**, not publishable benchmark scores,
until the controlled pilot protocol is signed off (`docs/PROJECT_LEAD_GUIDE.md`).

### Retail WS3 integration

WS3 adds a canonical 16-tool tau-retail contract, a deterministic shared
`RetailEnv`, framework wrapper contracts, standardized traces/final state, and
offline demo/dashboard tooling. This slice is designed to test whether
framework integrations behave consistently against the same stateful tools.

Public code supports E5 evaluation and replay workflows, while formal E5 cases,
gold, snapshots, hashes, raw traces, and evaluator output stay outside Git.
`verticals/retail/cases/RETAIL-E5-001.json` is a public `synthetic_fixture` for
tests and demos, not a formal E5 case. Synthetic smoke and demo artifacts are
technical validation only, not benchmark scores or framework rankings.

---

## 2. Five-minute quickstart

Goal: clone → configure → run **one smoke case** through all three frameworks →
see JSONL results and a terminal summary.

| Step | macOS / Linux | Expected outcome |
|---|---|---|
| 1. Clone | `git clone https://github.com/cmu-universal-agent/universal-agent-benchmark.git && cd universal-agent-benchmark` | Repository root with `adapter/`, `frameworks/`, `verticals/`, `scripts/` |
| 2. Check Python | `python3 --version` | **3.10 or newer** (3.9 fails on import) |
| 3. Configure API | `cp .env.example .env` then edit `.env` | Set at minimum `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| 4. Create venvs | `./scripts/setup_envs.sh` | Creates `.venv-openai`, `.venv-langgraph`, `.venv-crewai` |
| 5. Run smoke benchmark | `python3 scripts/run_benchmark.py` | Default task: `verticals/smoke_test/task_001.json` |

**After step 5 you should see:**

1. **Terminal** — lines like `experiment_id=exp-… model=gpt-…`, three framework
   runs, then a `--- Summary ---` block and `--- Failure Modes ---` per framework.
2. **File** — `results/metrics/smoke_test_results.jsonl` (gitignored) with **3
   appended lines**, one per framework. Each line is a serialized `AgentRunResult`
   (`task_id`, `framework`, `final_output`, `latency_seconds`, `model_name`,
   `tool_calls`, …).

Example summary line (values vary by model):

```text
          SMOKE-001   openai_agents_sdk (n=1): success_rate=100% json_valid_rate=100% instruction_following_rate=100% avg_latency=2.70s
```

Example JSONL row (truncated):

```json
{"task_id":"SMOKE-001","framework":"openai_agents_sdk","vertical":"smoke_test","final_output":"{...}","latency_seconds":2.7,"success":true,"model_name":"gpt-4o-mini",...}
```

If a venv is missing, `run_benchmark.py` prints `skipping <framework>: … not found`
and continues with the others.

---

## 3. Detailed workflow

Use **one Python** for orchestration scripts (`python3 scripts/…`). Each
framework still executes inside its own venv via subprocess.

### Stage 1 — Environment

| Action | macOS / Linux | Windows (PowerShell) |
|---|---|---|
| Copy env template | `cp .env.example .env` | `Copy-Item .env.example .env` |
| Install three venvs | `./scripts/setup_envs.sh` | `.\scripts\setup_envs.ps1` |
| Offline schema check (no API) | `.venv-openai/bin/python scripts/validate_contract_fixtures.py` | `.\.venv-openai\Scripts\python.exe scripts\validate_contract_fixtures.py` |

**.env variables (from `.env.example`):**

| Variable | Role |
|---|---|
| `OPENAI_API_KEY` | Required for live runs |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint |
| `OPENAI_MODEL` | Default model when `--model` is omitted |
| `OPENAI_MODEL_PROVIDER`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_OUTPUT_TOKENS`, `OPENAI_SEED` | Optional metadata passed to adapters |
| `BENCHMARK_EXPERIMENT_ID` | Optional; overridden by `run_benchmark.py --experiment-id` |
| `OPENAI_AGENTS_DISABLE_TRACING`, `CREWAI_DISABLE_TELEMETRY`, … | Telemetry toggles |

Never commit `.env`.

### Stage 2 — Data preparation

**Legacy vertical tasks (already in Git)** — optional refresh from public data:

| Script | macOS / Linux | Key flags |
|---|---|---|
| Medical (PubMedQA) | `python3 scripts/prepare_medical_tasks.py --cache-only` | `--overwrite` rebuilds `verticals/medical_diagnostic/task_*.json`; `--refresh` re-downloads cache; `--seed 42` |
| E-commerce (Amazon 2023) | `python3 scripts/prepare_ecommerce_tasks.py --cache-only` | Same flags as medical |

Without `--overwrite`, existing `task_*.json` files are **not** replaced.

**Eight-task core pilot (local only, under gitignored `data/`):**

Follow `docs/core_pilot_data_preparation.md`. Short sequence:

```bash
.venv-openai/bin/python scripts/validate_core_dataset_caches.py
.venv-openai/bin/python scripts/prepare_core_pilot.py --per-task 8 --overwrite
.venv-openai/bin/python scripts/validate_core_pilot.py --expected-per-task 8
.venv-openai/bin/python scripts/run_benchmark.py --task data/generated/core_pilot/cases --list-only
```

| `prepare_core_pilot.py` flag | Default | Meaning |
|---|---|---|
| `--output` | `data/generated/core_pilot` | Output root |
| `--tasks` | all eight IDs | Subset: H1 H2 H4 H5 E1 E2 E3 E5 |
| `--per-task` | 8 | Cases per task type |
| `--seed` | 42 | Deterministic sampling |
| `--overwrite` | off | Required to replace generated files |

### Stage 3 — Run benchmark

**Orchestrated run (recommended)** — `scripts/run_benchmark.py`:

| Flag | Default | Meaning |
|---|---|---|
| `--task` | `verticals/smoke_test/task_001.json` | Single JSON file **or** directory of `*.json` tasks |
| `--model` | from `.env` | Overrides `OPENAI_MODEL` for this invocation |
| `--experiment-id` | auto `exp-<uuid>` | Groups all runs in one session |
| `--repeats` | 1 | Repeat each (task, framework) pair |
| `--required-keys` | from task `metadata.evaluation` | Override expected JSON keys; omit check when sweeping mixed verticals |
| `--list-only` | off | Load cases and print metadata; **no API calls**, no JSONL writes |

| Goal | Command |
|---|---|
| Smoke (default) | `python3 scripts/run_benchmark.py` |
| Full legacy medical sweep | `python3 scripts/run_benchmark.py --task verticals/medical_diagnostic/` |
| Full legacy ecommerce sweep | `python3 scripts/run_benchmark.py --task verticals/ecommerce_trend_research/` |
| Controlled model session | `python3 scripts/run_benchmark.py --task verticals/medical_diagnostic/ --model gpt-4o-mini --experiment-id pilot-med-v1` |
| Repeat consistency | `python3 scripts/run_benchmark.py --task verticals/smoke_test/task_001.json --repeats 3` |

**Per-framework smoke (no JSONL orchestration)** — runs each adapter’s `run.py`
with its built-in default task:

| macOS / Linux | Windows |
|---|---|
| `./scripts/run_smoke_tests.sh` | `.\scripts\run_smoke_tests.ps1` |

Each framework `frameworks/*/run.py` accepts only `--task <path>`.

**Full legacy pipeline** (smoke + both verticals + reports):

```bash
./scripts/run_all.sh
```

Note: `run_all.sh` calls `python3 scripts/run_benchmark.py` three times, then
three analysis scripts. It does **not** run `setup_envs.sh` or prepare datasets.

**Tool contract tests** (one venv per invocation; simulates tool success/failure):

```bash
source .venv-openai/bin/activate
python scripts/test_tool_success.py --framework openai_agents_sdk
python scripts/test_tool_failure.py --framework openai_agents_sdk   # optional: --vertical medical_diagnostic|ecommerce_trend_research
deactivate
```

`--framework` choices: `openai_agents_sdk`, `langgraph`, `crewai`.

### Stage 4 — Analysis (reads existing JSONL; no API)

| Script | Arguments | Output |
|---|---|---|
| `scripts/report_hallucination_risk.py` | none | stdout tables: confidently-wrong vs ground truth |
| `scripts/report_medical_safety.py` | none | stdout: disclaimer / risky phrases / escalation |
| `scripts/generate_suitability_matrix.py` | none | **`results/framework_suitability_matrix.md`** |
| `scripts/check_result_fields.py` | none | **`results/framework_field_availability.md`** |

All analysis scripts read **`results/metrics/<vertical>_results.jsonl`**, keep the
**latest row per (task_id, framework)** (and per `model_name` where applicable).
If JSONL is empty, reports are empty or stale.

**Offline validation (no API):**

| Script | Purpose |
|---|---|
| `scripts/validate_tasks.py [--task PATH] [--require-v1]` | Legacy vs Benchmark Case Schema v1.0 |
| `scripts/validate_adapter_contracts.py` | Task loader, tool logs, output-schema checks |
| `scripts/validate_shared_tool_contracts.py` | No-tool / success / failure tool traces |
| `scripts/validate_dataset_specs.py` | H2/H4 spec consistency |
| `scripts/validate_contract_fixtures.py` | Valid/invalid schema fixtures in `tests/fixtures/` |

---

## 4. Reading `framework_suitability_matrix.md`

Generated by `scripts/generate_suitability_matrix.py` from local JSONL. The
committed copy may be **out of date** relative to your `.env` model; the header
warns when results are not tagged with the current model.

**Structure:**

1. **Header** — generation timestamp and model caveat.
2. **One section per vertical** (`Smoke Test`, `Medical Diagnostic Assistant`,
   `E-commerce Trend Researcher`) with a summary table:

   | Column | Meaning |
   |---|---|
   | `n` | Latest results counted for that framework |
   | `Accuracy` | Answer/trend direction vs `metadata.ground_truth` in legacy tasks |
   | `Confidently Wrong` | Wrong answer with high stated confidence |
   | `Medical Safety OK` | Medical vertical only: disclaimer + no risky phrases |
   | `Tool Overuse` | Unneeded tool calls on no-tool tasks |
   | `Avg Latency` | Mean `latency_seconds` |
   | `Failure Modes` | Breakdown of `failure_mode` from `adapter/evaluator.py` |

3. **ASCII bar charts** — quick visual compare for accuracy and latency.
4. **Qualitative Findings** — session notes (tool failure behavior, schema drift,
   model-specific typos); not automatically derived from the table.
5. **Recommendation** — narrative per vertical; interpret with the smoke caveat.

**Mini example (illustrative):**

```markdown
| Framework | n | Accuracy | Avg Latency | Failure Modes |
|---|---|---|---|---|
| openai_agents_sdk | 10 | 80% (8/10) | 3.6s | ok=10 |
| langgraph         | 10 | 80% (8/10) | 3.9s | ok=10 |
```

Here `ok=10` means all ten runs passed structural checks (`json_valid`, required
keys, instruction following). It does **not** mean 100% task accuracy — see the
Accuracy column. On branches with strict output validation, also watch
`output_schema_invalid` in `run_benchmark.py` summaries (not always repeated in
the matrix table).

---

## 5. Project layout

| Path | Responsibility |
|---|---|
| `adapter/` | Shared task loader, `BenchmarkTask` / `AgentRunResult`, evaluator, validation, JSONL writer |
| `frameworks/` | Thin per-framework runners: `openai_agents_sdk/`, `langgraph_agent/`, `crewai_agent/` |
| `verticals/` | Committed legacy task JSON + per-vertical mock `tools.py` |
| `schemas/` | Draft JSON Schemas: benchmark case, healthcare/ecommerce output, tool call, run log |
| `scripts/` | Setup, dataset prep, benchmark orchestration, validation, reports |
| `results/` | Committed reports (`framework_suitability_matrix.md`, …); **`results/metrics/` is gitignored** |
| `evaluator_data/` | Evaluator-only gold/rubric templates — **never** passed to agents |
| `data/` | Gitignored dataset caches and `generated/core_pilot/` outputs |
| `docs/` | Project guides, dataset prep, stress testing, schema review |
| `tests/` | Unit tests and schema contract fixtures |
| `mappings/`, `splits/`, `tools/` | Label mappings, split manifests, tool registry drafts |

---

## 6. Advanced usage

### Custom tasks

1. Add `task_XXX.json` under a vertical directory (legacy shape) **or** a
   Benchmark Case Schema v1.0 file (`schema_version: "1.0"`, see
   `schemas/benchmark_case.schema.json`).
2. Validate: `.venv-openai/bin/python scripts/validate_tasks.py --task verticals/your_vertical/`
3. Run: `python3 scripts/run_benchmark.py --task verticals/your_vertical/task_XXX.json`

Legacy tasks support optional `metadata.evaluation` with `required_keys`,
`exact_values`, and `one_sentence_fields` — used by `run_benchmark.py` unless
you pass `--required-keys`.

### Switch models fairly

Use one `--experiment-id` and one `--model` for the entire session so all three
frameworks are comparable:

```bash
python3 scripts/run_benchmark.py \
  --task verticals/medical_diagnostic/ \
  --model gpt-4o-mini \
  --experiment-id exp-20260721-med
```

Do not mix JSONL rows from different models when reading reports unless you filter
by `model_name` (legacy rows without `model_name` appear as `unknown`).

### Legacy vs Benchmark Case Schema v1.0

| | Legacy (`verticals/*/task_*.json`) | v1.0 (`schema_version: "1.0"`) |
|---|---|---|
| Shape | `task_id`, `vertical`, `prompt`, `metadata` | `case_id`, `input`, `allowed_tools`, `stress_type`, `metadata`, … |
| Loader | `adapter/task_loader.py` renders v1 `input` into a prompt | Enforces `allowed_tools` on all adapters |
| Validation | `validate_tasks.py` → `LEGACY` | `validate_tasks.py` → `V1 PASS` |
| Formal pilot | Regression / smoke | Target format for eight-task pilot under `data/generated/core_pilot/cases/` |

After migration: `scripts/validate_tasks.py --require-v1` exits non-zero if any
legacy file remains.

Ground truth for scoring stays **out of agent-visible cases** — in v1 pilot,
evaluator gold lives under `data/generated/core_pilot/gold/` and
`evaluator_data/` (see `evaluator_data/README.md`).

### Integration and contribution notes

Use `main` as the integration base. Check GitHub before starting work rather
than relying on historical feature branches or stale local remote-tracking
refs.

Before opening a PR:

- Branch from the integration branch your work depends on (not from stale clones).
- Do **not** commit `.env`, `.venv-*`, `data/`, `results/metrics/`, or
  evaluator-only gold with answers.
- Preliminary smoke results belong in labelled reports — not as final benchmark
  rankings (`docs/PROJECT_LEAD_GUIDE.md`).

Task validation before push (offline):

```bash
.venv-openai/bin/python scripts/validate_tasks.py
.venv-openai/bin/python scripts/validate_adapter_contracts.py
```

---

## 7. Documentation index

Read in this order:

1. **This README** — setup, commands, results layout.
2. **`docs/PROJECT_LEAD_GUIDE.md`** — durable coordination context, owners,
   WS2/WS3 gates, privacy boundaries, and validation commands. Query GitHub for
   mutable PR, branch, review, and merge state.
3. **`docs/core_pilot_data_preparation.md`** — eight-task dataset caches and
   `prepare_core_pilot.py` workflow (when you move beyond legacy 20 cases).
4. **`docs/framework_comparison_rationale.md`** — experiment tiers, control
   variables, and comparison dimensions.
5. **`docs/schema_field_review.md`** — approved schema fields and pending
   proposals (including stress metadata in §10 on the stress branch).
6. **`docs/stress_testing_README.md`** — stress-testing design and fixture
   guidance.
7. **`docs/current_status_and_handoff.md`** — **historical** WS2 snapshot
   (2026-07-16); use only for background. The banner at the top points to the
   project lead guide for anything current.

Supporting references: `docs/dataset_gold_generation_plan.md`,
`docs/workstream_2_summary.md`, `results/preliminary_technical_smoke_20260717.md`.

## Retail run console (dashboard)

```bash
python3 scripts/generate_dashboard.py --vertical retail   # writes results/dashboard.html
open results/dashboard.html                                # macOS; or just double-click the file
```

Reads the latest row per `(case_id, framework, experiment_label)` from
`results/metrics/retail_results.jsonl` and renders a self-contained, read-only
HTML page — no server, nothing to deploy. The public view is explicitly
synthetic technical validation, not benchmark scoring: it publishes sanitized
trace summaries and aggregate final-state verdicts only. `results/dashboard.html`
is generated (gitignored), so it isn't checked in or viewable on GitHub —
regenerate it locally and open the file to view it.

Official repository: <https://github.com/cmu-universal-agent/universal-agent-benchmark>
