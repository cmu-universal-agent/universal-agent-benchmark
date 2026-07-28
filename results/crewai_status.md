# CrewAI Workstream 2 Status

This document describes the CrewAI-specific adapter at CrewAI 1.15.1. It is
maintained separately from generated cross-framework result tables.

## Verified environment

- CrewAI 1.15.1 installed successfully on Windows with Python 3.12.
- `pip check` reported no broken requirements.
- The fully pinned requirements resolve for CPython 3.12 on both
  `x86_64-pc-windows-msvc` and `x86_64-manylinux_2_28`. Windows was also
  installed and exercised locally. Linux dependency resolution passed, but a
  native Linux test run is still required in Linux CI or on a teammate's Linux
  machine; package resolution alone is not an execution claim.
- The pinned `grpcio==1.82.0` release is yanked on PyPI because its protobuf
  dependency declaration is incorrect. It is part of the current CrewAI
  environment freeze and is pulled transitively through CrewAI's Chroma and
  OpenTelemetry dependencies. The project also pins compatible
  `protobuf==6.33.6`; installation and `pip check` pass on the verified Windows
  environment. Coordinate any dependency refresh rather than changing this
  pin in isolation.
- The installed `LLM` model accepts `provider`, `temperature`, `max_tokens`,
  and `seed`. The adapter forwards shared run configuration through those
  parameters. “Forwarded” does not mean every provider/model enforces a
  parameter.
- CrewAI tracing and anonymous telemetry default to disabled before CrewAI is
  imported. Explicit process or `.env` settings can still override these
  defaults when a developer intentionally wants CrewAI telemetry.
- CrewAI gives `CrewOutput.token_usage` a default all-zero value. The adapter
  treats that value as unavailable when `successful_requests` is zero or
  absent.
- `CREWAI_STORAGE_DIR` remains project-local. CrewAI 1.15.1 also initializes a
  separate credential store during import and exposes no path setting for it.
  The adapter redirects only that storage-path provider to the project-local
  `.crewai/credentials` directory (or `CREWAI_CREDENTIAL_STORAGE_DIR`) before
  importing CrewAI; CrewAI still owns encryption and atomic credential writes.

## Field availability

| Field | Classification | CrewAI adapter behavior |
|---|---|---|
| Token usage | Supported and captured | Provider-reported prompt, completion, and total tokens are normalized. Missing fields remain null. Cached, reasoning, cache-creation, and successful-request counts are retained in `raw_metadata` when available. |
| Tool calls | Supported and captured | Calls made through the registered shared benchmark wrappers are normalized by the shared runtime. A prompt cannot expose a tool omitted from `allowed_tools`. |
| Tool errors | Supported and captured | Errors raised inside shared tool wrappers are retained in normalized tool traces. CrewAI-side failures that occur before a wrapper starts cannot produce a shared wrapper trace. |
| Run-level errors | Supported and captured | `run_task` returns `success=false` with the exception type and a credential-redacted message. |
| End-to-end latency | Supported and captured | Shared `begin_run`/`finish_run` measure wall-clock run latency, including model and tool work. |
| Tool latency | Supported and captured | Shared tool wrappers record per-call latency and the shared runtime preserves it. |
| Framework version | Supported and captured | Shared runtime reads the installed `crewai` distribution version. |
| Model provider and name | Supported and captured | Shared runtime records both; the same values are forwarded to CrewAI's `LLM`. |
| Temperature | Supported and captured | Recorded by the shared runtime and forwarded to CrewAI. Provider/model enforcement must be verified during live execution. |
| Maximum output tokens | Supported and captured | When configured, shared `max_output_tokens` is forwarded as CrewAI `max_tokens`. Provider/model enforcement must be verified during live execution. |
| Seed | Unavailable or unreliable | CrewAI 1.15.1 accepts and forwards `seed`, and the adapter does so when configured. Deterministic enforcement depends on the provider/model and must not be assumed. |
| Raw output | Supported and captured | Unmodified string output is stored in both shared `final_output` and `raw_output`. |
| Raw metadata | Supported and captured | Shared adapter metadata is augmented with token-availability details, additional CrewAI usage fields, forwarded-setting names, and selected tool names. No API keys are recorded. |
| Prohibited tool attempts | Supported by CrewAI but not currently captured | Tool filtering prevents exposure, but an attempted name that was never supplied to the Agent does not create a CrewAI/shared tool-call event. |
| Provider retry details and partial failure usage | Supported by CrewAI but not currently captured | A failed kickoff does not reliably expose a `CrewOutput`, so partial token totals and provider retry details are unavailable through the current execution boundary. |
| Canonical E5 tau-retail calls and simulator state | Requires shared infrastructure | The repository does not yet expose the tau-retail tool registry/simulator bridge used by all frameworks. CrewAI can discover E5 cases but cannot perform valid live E5 execution until that shared bridge exists. |
| Formal run-log schema serialization | Requires shared infrastructure | The adapter writes the existing flat `AgentRunResult` through `append_result`; it does not introduce a second result format. |

## Tool policy

- `allowed_tools=None`: all registered tools for the runtime vertical, for
  legacy compatibility.
- `allowed_tools=[]`: no tools.
- A valid name: only the matching tool in the task's vertical.
- Unknown or wrong-vertical names: no matching tool.
- Filtering occurs before CrewAI Agent construction. Prompt text cannot add a
  tool.

Only the legacy medical literature and e-commerce review-history tools are
currently registered. H1, H2, H4, H5, E1, E2, and E3 cases without live tools
can execute. Valid E5 live execution remains blocked on shared tau-retail
infrastructure.

## Core execution and validation

`frameworks/crewai_agent/run_core.py` accepts either one generated case file or
the flat `data/generated/core_pilot/cases` directory produced by
`scripts/prepare_core_pilot.py`. It orders cases by the approved task order
H1, H2, H4, H5, E1, E2, E3, E5 and then by case ID. `--list-only` and
`--dry-run` perform discovery without model calls or result writes.

`frameworks/crewai_agent/check_results.py` reconstructs every row as the shared
`AgentRunResult`, checks duplicate case IDs within an experiment and validates
normalized tool traces against the shared schema, summarizes task and status
counts, and reports missing metadata, usage, and malformed successful outputs.
It does not calculate rankings. A completed failed case is appended, later
cases continue, and the core runner exits nonzero if any case fails.

The preparation script defaults to eight cases for each of the eight core task
types, for 64 cases when all source datasets are available. The generated case
directory is intentionally absent until dataset preparation runs and is ignored
by Git. Unit coverage also feeds one synthetic schema-v1 case for every core
task through the list-only entry point and confirms that it makes zero model
calls and zero result writes.

### Windows

```powershell
.\scripts\setup_envs.ps1
.\.venv-crewai\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-crewai\Scripts\python.exe frameworks\crewai_agent\run_core.py --task data\generated\core_pilot\cases --list-only
.\.venv-crewai\Scripts\python.exe frameworks\crewai_agent\run_core.py --task data\generated\core_pilot\cases --experiment-id crewai-core-live --output results\metrics\crewai_core_results.jsonl
.\.venv-crewai\Scripts\python.exe frameworks\crewai_agent\check_results.py --input results\metrics\crewai_core_results.jsonl
```

### Linux

```bash
bash scripts/setup_envs.sh
.venv-crewai/bin/python -m unittest discover -s tests -v
.venv-crewai/bin/python frameworks/crewai_agent/run_core.py --task data/generated/core_pilot/cases --list-only
.venv-crewai/bin/python frameworks/crewai_agent/run_core.py --task data/generated/core_pilot/cases --experiment-id crewai-core-live --output results/metrics/crewai_core_results.jsonl
.venv-crewai/bin/python frameworks/crewai_agent/check_results.py --input results/metrics/crewai_core_results.jsonl
```

When a result directory contains rows from other frameworks, pass only the
CrewAI JSONL file(s) to the checker; non-CrewAI rows are validation errors.
