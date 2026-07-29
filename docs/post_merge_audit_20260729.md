# Post-merge audit — 2026-07-29

Verified baseline: official `main` at `8de017833581f744bea610d900fc7c792b7869bb`.

This is a read-only audit of the concentrated 2026-07-28 merges. It records
technical validation and remaining gates; it does not publish E5 evaluator-only
cases, gold, traces, or benchmark scores.

## Outcome

The canonical contract and shared retail core survived the merge correctly:

- contract `0.2.0` contains all 16 canonical tools;
- PR #10's call/result/trace isolation fix is present;
- the shared core's 38 offline tests pass;
- the LangGraph retail wrapper's six focused tests pass;
- no private E5 markers from the approved review batch were found in `main`.

WS3 is not complete. One LangGraph parity defect is reproducible, only one of
three WS3 wrappers exists, and Chloe's approved E5 work is still local-only and
not integrated into a public-safe evaluator path.

## Findings

### P1 — LangGraph invalid arguments bypass the shared core

Files:

- `adapter/retail_tool_factory.py`
- `frameworks/langgraph_agent/retail_evidence.py`
- `frameworks/langgraph_agent/retail_tools.py`

The wrapper binds a Pydantic `args_schema` before calling
`RetailEnv.call_tool()`. Missing required arguments therefore raise a
`ValidationError` before the core can record `invalid_arguments`; unexpected
arguments are silently dropped by the Pydantic model.

Reproduction on merged `main`:

```text
MISSING_ARGS_EXCEPTION ValidationError
MISSING_ARGS_TRACE_COUNT 0
EXTRA_ARGS_OK True
EXTRA_ARGS_TRACE_ARGUMENTS {'order_id': 'O5001'}
```

The offline evidence test does not catch this because its invalid-arguments
scenario calls `env.call_tool()` directly instead of invoking the LangGraph
tool. The wrapper can therefore report passing parity evidence while its real
invalid-argument path is different.

Required action: route validation failures through the core, preserve the
original arguments, and add a wrapper-level regression test asserting a traced
`invalid_arguments` result.

### P1 — Only one of three WS3 retail wrappers exists

Merged `main` contains:

- LangGraph: retail wrapper, offline evidence builder, and tests;
- CrewAI: WS2/core runner only, no `RetailEnv` wrapper or WS3 evidence;
- OpenAI Agents SDK: no `RetailEnv` wrapper or WS3 evidence.

There are no open pull requests. The hard parity gate requiring identical
offline evidence from all three frameworks is therefore still open.

Required action: add thin CrewAI and OpenAI Agents SDK wrappers against the
existing `RetailEnv` and run the same seven evidence scenarios.

### P1 — Approved E5 semantics and cases are not integrated

Chloe confirmed the four E5 case/gold records on 2026-07-29. The updated local
evaluator smoke passes 11/11 controls and the four synthetic case-review
positive examples pass 4/4.

Merged `main` still:

- has no `adapter/e5_evaluator.py`, `scripts/run_e5_smoke.py`, or approved E5
  semantics document;
- marks `verticals/retail/cases/RETAIL-E5-001.json` as
  `pending_chloe_approval`;
- derives E5 review samples directly from raw tau tasks in
  `prepare_core_pilot.py` rather than consuming the approved batch;
- has no pinned DB snapshot/hash, expected final hashes, or clean gold replay.

Raw `E5_cases_batch1.json`, gold examples, expected calls, hashes, and generated
private review output must remain evaluator-only and must not be committed to
this public repository.

Required action: create a separate public-safe E5 integration PR containing
only evaluator implementation, corrected semantics documentation, conversion
code that reads a gitignored local batch, and synthetic tests.

### P2 — Dashboard loses rows across experiment labels

File: `scripts/generate_dashboard.py`.

Python correctly keeps one result per
`(case_id, framework, experiment_label)`, but the generated JavaScript indexes
runs only by `(case_id, framework)`. When the same case/framework has both
`technical_smoke` and `pilot` rows, the later row overwrites the earlier one
and one label renders a blank cell.

Required action: include `experiment_label` in `runByDomKey`, lookup keys, and
drawer keys, then add a rendered-output regression test with two labels.

### P2 — Dashboard prototype uses stale tool semantics

File: `docs/WS3_dashboard_prototype.html`.

The sample traces call `transfer_to_human_agents` with non-canonical
`order_id`/`reason` arguments and mark it as mutating. Contract `0.2.0` accepts
only `summary` and classifies the tool as non-mutating.

Required action: regenerate or edit the synthetic prototype to use canonical
arguments and `mut:false`.

### P2 — No automated merge gate and no portable full-suite command

The repository has no `.github/workflows`. PRs #8, #9, #10, and #12 were merged
with no recorded checks and no formal approval decision; PR #4 was approved.

Environment results on merged `main`:

- CrewAI environment: full discovery, 137 tests passed, 12 skipped;
- OpenAI environment: full discovery failed on two CrewAI import errors;
- LangGraph environment: full discovery failed on the same two CrewAI import
  errors;
- targeted OpenAI, LangGraph, CrewAI, shared-core, and contract checks pass.

Required action: define one environment-aware offline test command and add a
minimal GitHub Actions matrix before further concentrated merges.

### P2 — Required methodology/limitations delivery is absent

The project guide names a concise WS3 methodology/limitations record as a hard
MVP deliverable. No dedicated artifact is present on merged `main`.

Required action: add the short methodology/limitations note before reporting
WS3 completion.

### P3 — Repository status documentation is stale

- `README.md` still describes PRs #3, #4, #8, and #9 as proposed branches even
  though they are merged.
- `docs/PROJECT_LEAD_GUIDE.md` is last verified on 2026-07-22 and still carries
  the pre-merge hold/state.
- the tracked synthetic retail fixture still says Chloe approval is pending.
- `demo_ws3_offline.py` still describes all wrappers as future work.

Required action: update status prose after the technical P1/P2 fixes are
assigned. Do not put mutable PR head SHAs into a branch that changes them.

## Validation evidence

Passed:

```text
LangGraph retail wrapper: 6/6
Shared retail core: 38/38
CrewAI full suite: 137 passed, 12 skipped
OpenAI targeted generation-setting suite: 9/9
WS3 contract validator: version=0.2.0 tools=16 schemas=20 scenarios=7 calls=8
Contract fixtures, adapter contracts, shared tool contracts: passed
Python compileall: passed
Private E5 marker scan: no matches
```

Expected/non-scoring limitations:

- no live model calls were made;
- no benchmark scores or framework rankings were produced;
- evaluator-only E5 files remain local;
- real E5 final-state replay still needs the pinned DB snapshot and hashes.

## Recommended sequence

1. Fix the LangGraph invalid-argument path and add its regression test.
2. Integrate the public-safe E5 evaluator/docs path after Chloe's approval.
3. Add CrewAI and OpenAI Agents SDK retail wrappers with identical evidence.
4. Fix the dashboard label key and prototype contract drift.
5. Add the test matrix and methodology/limitations note.
6. Refresh README/project status only after the above heads are known.
