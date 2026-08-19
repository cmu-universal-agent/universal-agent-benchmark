# Universal Agent Benchmark

Compare **LangGraph**, **CrewAI**, and **OpenAI Agents SDK** under one controlled
protocol across eight healthcare and ecommerce/retail task families. The
benchmark asks **where each framework breaks** while holding the model,
agent-visible cases, generation settings, run policy, result contract, and
task-specific evaluation fixed. All adapters share `adapter/` for task loading,
result shape, deterministic evaluation, attempt tracking, and JSONL logging.

## Current delivery status

The formal controlled pilot is protocol `pilot-60-v2.0`, revision r10, executed
at commit `f58baa77c7474ac2830113efa13ecc3abd63a2db`.

- 24/24 fresh readiness preflights completed before result execution.
- 180/180 main runs and 48/48 targeted repeats completed: 228 formal result
  logical runs (229 attempts after one eligible infrastructure retry), or 252
  logical runs including preflight.
- Scoring, data QA, H5 aggregation, and C1–C6 claims review are complete; C4
  retains a non-blocking phrasing reservation.
- Public aggregate release remains pending explicit owner authorization.
- All v1.x attempts and superseded v2.0 candidates remain immutable, excluded
  `technical_smoke_only` evidence.

Formal cases, gold, raw traces, run identifiers, hashes, and evaluator-only
artifacts remain private. The public repository contains implementation,
schemas, sanitized fixtures, reproducibility documentation, and only
privacy-reviewed aggregate candidates.

## Benchmark at a glance

| Dimension | Formal controlled pilot |
|---|---|
| Frameworks | OpenAI Agents SDK, LangGraph, CrewAI |
| Task families | H1 answer/evidence/safety; H2 urgency/escalation; H4 extraction; H5 boundary/refusal; E1 trend; E2 recommendation; E3 policy; E5 stateful retail tools |
| Cases | 60 frozen cases: 8 each for H1/H2/H4/H5/E1/E2/E3 and 4 for E5 |
| Execution | 24 readiness preflights + 180 main logical runs + 48 targeted repeats |
| Evaluation | Deterministic H1/H2/H4/E1/E2/E3 scoring; H5 human criterion annotation plus deterministic aggregation; E5 response-contract and local replay evaluation |
| Reproducibility | Exact execution commit, three isolated Python 3.12 environments, append-only attempts, exact-repeat selection, 300-second timeout |
| Publication boundary | Aggregate-safe documentation only; evaluator-only inputs and raw execution evidence remain local |

**Requirements:** Python **3.10–3.13** (the pinned CrewAI 1.15.1 requires
Python `<3.14`), network access for setup and model calls, and an
OpenAI-compatible API key in `.env`.

---

## 1. Benchmark scope and architecture

| Dimension | Healthcare | Ecommerce / retail |
|---|---|---|
| Formal task families | H1, H2, H4, H5 | E1, E2, E3, E5 |
| Frozen formal cases | 32 | 28 |
| Evaluation focus | Accuracy, evidence, confidence, urgency, escalation, extraction, refusal, safety | Trend, recommendations, constraints, policy, tool actions, response contract, replayed final state |
| Stateful environment | None required for content tasks | E5 uses the shared 16-tool Retail environment |

The public `verticals/` task JSON files are developer regression and synthetic
fixtures. They are not substitutes for the frozen private 60-case manifest.
The formal cases are built from public datasets but remain local with their
evaluator-only gold; see [Data preparation](#stage-2-data-preparation).
Preliminary runs in `results/` are engineering smoke, not formal benchmark
scores.

### Unified execution path

```text
agent-visible case
  -> shared loader and task/E5 routing
  -> unified runner and isolated framework subprocess
  -> normalized AgentRunResult + append-only attempt ledger
  -> task-specific deterministic evaluator or local E5 replay
  -> privacy-reviewed aggregate -> report/dashboard candidate
```

The runner uses one logical-run identity across frameworks, preserves every
attempt, permits at most one documented infrastructure retry, and keeps cases,
repeats, and retries distinct. A completed low score, wrong answer, invalid
output, or evaluator failure is a frozen result and is never rerun for score.

### Stateful E5 specialization

E5 uses a canonical 16-tool tau-retail contract, deterministic shared
`RetailEnv`, three framework-native wrappers, standardized traces/final state,
and a local authoritative replay evaluator. This is one task family within the
overall benchmark, not a separate benchmark result stream.

Public code supports E5 evaluation and replay workflows, while formal E5 cases,
gold, snapshots, hashes, raw traces, and evaluator output stay outside Git.
`verticals/retail/cases/RETAIL-E5-001.json` is a public `synthetic_fixture` for
tests and demos, not a formal E5 case. Synthetic smoke and demo artifacts are
technical validation only, not benchmark scores or framework rankings.
See `docs/ws3_methodology_and_limitations.md` for the validation protocol,
privacy boundary, exclusions, and known limitations.

---

## 2. Five-minute developer-smoke quickstart

Goal: clone → configure → run **one smoke case** through all three frameworks →
see JSONL results and a terminal summary.

This workflow exercises the public smoke fixture and may make paid model calls.
It does not reproduce the frozen formal v2.0 pilot or create formal benchmark
evidence.

| Step | macOS / Linux | Expected outcome |
|---|---|---|
| 1. Clone | `git clone https://github.com/cmu-universal-agent/universal-agent-benchmark.git && cd universal-agent-benchmark` | Repository root with `adapter/`, `frameworks/`, `verticals/`, `scripts/` |
| 2. Check Python | `python3 --version` | **3.10–3.13** (3.9 fails on import; CrewAI 1.15.1 rejects 3.14) |
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

This workflow prepares a local review candidate. It does not recreate the
frozen r10 manifest or evaluator-only gold, which remain private and versioned
outside Git.

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
| `--per-task` | 8 | Maximum cases per task type; E5 is capped by its four owner-approved cases |
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
| `--repeat` | off | Run one exact positive repeat number without touching earlier repeats |
| `--framework` | all | Run all frameworks or one named framework |
| `--timeout-seconds` | 300 | Per-attempt framework subprocess timeout |
| `--rerun-reason` | off | Required when retrying an existing logical run |
| `--required-keys` | from task `metadata.evaluation` | Override expected JSON keys; omit check when sweeping mixed verticals |
| `--list-only` | off | Load cases and print metadata; **no API calls**, no JSONL writes |

| Goal | Command |
|---|---|
| Smoke (default) | `python3 scripts/run_benchmark.py` |
| Full legacy medical sweep | `python3 scripts/run_benchmark.py --task verticals/medical_diagnostic/` |
| Full legacy ecommerce sweep | `python3 scripts/run_benchmark.py --task verticals/ecommerce_trend_research/` |
| Controlled model session | `python3 scripts/run_benchmark.py --task verticals/medical_diagnostic/ --model gpt-4o-mini --experiment-id pilot-med-v1` |
| Repeat consistency | `python3 scripts/run_benchmark.py --task verticals/smoke_test/task_001.json --repeats 3` |

When the task path is `data/generated/core_pilot/cases`, the runner loads the
sibling gitignored `gold/` directory and reports deterministic content metrics
for H1, H2, H4, H5, E1, E2, and E3. E5 remains on its dedicated response-contract
and simulator-state evaluator.

Formal reruns are infrastructure-only, must target the failed logical run and
exact repeat, and may not be used to improve a completed model result.

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

The first three legacy/smoke analysis scripts use the shared loader, which
keeps the latest attempt for each
`(case_id, framework, experiment_id, logical_run_id)` without folding cases or
repeats. `check_result_fields.py` instead scans every historical JSONL row to
audit field availability across format changes. None of these scripts is the
formal r10 aggregate/report pipeline; if JSONL is empty, reports are empty or
stale.

**Offline validation (no API):**

| Script | Purpose |
|---|---|
| `scripts/validate_tasks.py [--task PATH] [--require-v1]` | Legacy vs Benchmark Case Schema v1.0 |
| `scripts/validate_adapter_contracts.py` | Task loader, tool logs, output-schema checks |
| `scripts/validate_shared_tool_contracts.py` | No-tool / success / failure tool traces |
| `scripts/validate_dataset_specs.py` | H2/H4 spec consistency |
| `scripts/validate_contract_fixtures.py` | Valid/invalid schema fixtures in `tests/fixtures/` |

---

## 4. Legacy/smoke report interpretation

`framework_suitability_matrix.md` is a developer/legacy report generated by
`scripts/generate_suitability_matrix.py` from local JSONL. It is not the formal
r10 report or aggregate pipeline. The committed copy may be **out of date**
relative to your `.env` model; the header warns when results are not tagged
with the current model. For the controlled-pilot delivery, start with
`docs/experiment_report_skeleton.md` and `docs/ws5/README.md`.

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
| `verticals/` | Public developer smoke/regression tasks and the synthetic Retail E5 fixture |
| `schemas/` | Draft JSON Schemas: benchmark case, healthcare/ecommerce output, tool call, run log |
| `scripts/` | Setup, dataset prep, benchmark orchestration, validation, reports |
| `results/` | Committed reports (`framework_suitability_matrix.md`, …); **`results/metrics/` is gitignored** |
| `evaluator_data/` | Evaluator-only gold/rubric templates — **never** passed to agents |
| `data/` | Gitignored dataset caches and `generated/core_pilot/` outputs |
| `docs/` | Formal protocol/report, WS5 findings and limitations, methodology, dataset prep, historical design notes |
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
  rankings (`docs/framework_comparison_rationale.md`).

Task validation before push (offline):

```bash
.venv-openai/bin/python scripts/validate_tasks.py
.venv-openai/bin/python scripts/validate_adapter_contracts.py
```

---

## 7. Documentation index

Read in this order:

1. **This README** — setup, commands, results layout.
2. **`docs/formal_benchmark_protocol_v2.0.md`** — frozen v2.0 protocol, gates,
   execution counts, privacy boundary, and rerun policy.
3. **`docs/experiment_report_skeleton.md`** — formal execution/scoring status
   and approved claims boundary.
4. **[WS5 delivery package](docs/ws5/README.md)** — owner-approved findings,
   adjudicated failures, limitations, exclusions, and publication boundary.
5. **`docs/representative_case_ids.md`** — approved representative IDs and
   logical-run arithmetic.
6. **`docs/ws3_methodology_and_limitations.md`** — Retail/E5 methodology,
   exclusions, and limitations.
7. **`docs/core_pilot_data_preparation.md`** — eight-task dataset caches and
   `prepare_core_pilot.py` workflow (when you move beyond legacy 20 cases).

Historical/design references include `docs/controlled_pilot_protocol.md`,
`docs/framework_comparison_rationale.md`, `docs/schema_field_review.md`, and
`docs/stress_testing_README.md`. Stress testing is deferred and is not part of
the formal controlled-pilot denominator.

## 8. Dashboards and specialist tooling

### Controlled-pilot dashboard

```bash
python3 scripts/generate_pilot_dashboard.py
python3 scripts/generate_pilot_dashboard.py \
  --aggregate path/to/privacy-reviewed-aggregate.json \
  --freeze-confirmation path/to/matching-freeze-confirmation.json
```

The default output is a public-safe placeholder. A result-bearing candidate is
rendered only when both matching, allowlisted inputs pass validation. The
generated `results/pilot_dashboard.html` remains gitignored, and a valid
candidate is not authorized for public release until the owner grants that
separate permission.

### Synthetic Retail/E5 integration dashboard

```bash
python3 scripts/generate_dashboard.py --vertical retail   # writes results/dashboard.html
python3 scripts/generate_dashboard.py --vertical retail --synthetic-walkthrough
python3 scripts/serve_ws3_playground.py                    # http://127.0.0.1:8765
open results/dashboard.html                                # macOS; or just double-click the file
```

Reads the latest row per `(case_id, framework, experiment_label)` from
`results/metrics/retail_results.jsonl` and renders a self-contained, read-only
HTML page — no server, nothing to deploy. The public view is explicitly
synthetic technical validation, not benchmark scoring: it publishes sanitized
trace summaries and aggregate final-state verdicts only. `results/dashboard.html`
is generated (gitignored), so it isn't checked in or viewable on GitHub —
regenerate it locally and open the file to view it.
Use `--synthetic-walkthrough` for the meeting-ready public case input and
sanitized contract-validation output; it does not create framework scores.
Use `serve_ws3_playground.py` for the interactive meeting page: enter a request,
choose a merged wrapper, and run it locally with `OPENAI_API_KEY` configured.
Live responses expose only the agent answer and an allowlisted trace; they are
not written to `results/metrics`. The offline replay remains available without
a model call.

Official repository: <https://github.com/cmu-universal-agent/universal-agent-benchmark>
