# WS3 Retail Dashboard Contract

Status: **frozen v1.0**
Freeze date: 2026-08-10
Owner: Xiaoxia
Scope: `scripts/generate_dashboard.py` only — its jsonl input contract and its
rendered chart/section specifications.

This freezes the integration surface between `results/metrics/retail_results.jsonl`
and the public `results/dashboard.html`. It does not change any behavior; it
records the behavior already implemented and verified in this repository as of
the freeze date. Any future change to field-reading or chart logic in
`scripts/generate_dashboard.py` must bump this doc's version and update the
regression tests in `tests/test_generate_dashboard.py` (see "Enforcement"
below) in the same change.

This doc assumes familiarity with `docs/ws3_tau_retail_contract.md`, which
freezes the upstream tool/state/error contract that trace and final-state data
originate from. It does not restate that contract.

## Aggregate input contract

Source: one JSON object per line in `results/metrics/<vertical>_results.jsonl`
(`adapter.result_writer.default_result_path`), read by
`_load_latest_dashboard_results` (generate_dashboard.py:181-200) and shaped by
`_build_run` (generate_dashboard.py:161-178).

### Required fields

| Field | Notes |
|---|---|
| `framework` | Used verbatim; rows whose framework is not in the public allowlist (below) are dropped. |
| `task_id` | Used only as a `case_id` fallback (`row.get("case_id") or row["task_id"]`); a `KeyError` propagates if both are absent. |

### Optional fields (top-level row, falling back to `raw_metadata`)

Resolved via `_first_present(row, raw, key)` (generate_dashboard.py:81-88),
which checks the top-level row first, then `row["raw_metadata"]`, and returns
`None` if neither has a non-null value — it never guesses a default beyond
what's listed here.

| Field | Default if absent | Transform |
|---|---|---|
| `case_id` | falls back to `task_id` | none |
| `experiment_label` | `"unknown"` | none |
| `runtime_status` | `"unknown"` | none |
| `schema_valid` | `None` | kept only if `isinstance(value, bool)`, else `None` |
| `final_state_correct` | `"not_available"` | mapped by `_final_state_verdict` (generate_dashboard.py:153-158): `True → "correct"`, `False → "incorrect"`, anything else → `"not_available"` |
| `trace` | `None` | sanitized by `_sanitize_trace` (see below) |

### `trace` sanitization (generate_dashboard.py:114-150)

`trace` must be a list of dicts to be processed; `None` or any non-list value
becomes `None`, and non-dict list entries are silently skipped. Each surviving
step is reduced to exactly:

| Output field | Read from | Fallback |
|---|---|---|
| `index` | `step["index"]` or `step["sequence_index"]` | enumerate position; used if not an `int` |
| `tool_name` | `step["tool_name"]` or `step["tool"]` | `"unknown_tool"` |
| `outcome` | `"ok"` if `step["ok"] is True`; else `str(error_code)` if truthy (`error_code` falls back to `step["error"]["error_type"]`); else `"error"` if `step["ok"] is False`; else `"unknown"` | — |
| `state_changed` | `step["state_changed"]` or `step["mut"]`, coerced to strict `True` | `False` |

### Fields never read from the jsonl for the dashboard

`arguments`, `result`, `state_before_sha256`, `state_after_sha256`,
`final_state`, `expected_state`, `evaluator_output`. Enforced by
`tests/test_generate_dashboard.py`'s private-field allowlist test — do not
add these to the payload without an explicit privacy review.

### Dedup rule

`_load_latest_dashboard_results` keys rows by `(case_id, framework,
experiment_label)` and iterates the file top-to-bottom; the **last** matching
line wins. There is no timestamp comparison — "latest" means latest in file
order, not latest by any embedded time field.

### Framework and label allowlisting

- `PUBLIC_EVIDENCE_FRAMEWORKS` (generate_dashboard.py:63-67) = frameworks in
  `FRAMEWORK_EVIDENCE` (generate_dashboard.py:46-62) with `status ==
  "available"`. Currently all three: `langgraph`, `openai_agents_sdk`,
  `crewai`. Rows for any other framework are dropped in `build_payload`
  (generate_dashboard.py:312).
- `KNOWN_FRAMEWORK_ORDER = ["langgraph", "openai_agents_sdk", "crewai"]`
  (generate_dashboard.py:37) fixes display order; `_collect_frameworks`
  always emits a card per entry in this list regardless of jsonl content.
- `LABEL_PREFERENCE = ["technical_smoke", "pilot", "benchmark"]`
  (generate_dashboard.py:42) — `_default_label` (generate_dashboard.py:230-234)
  picks the first of these present among the run labels; otherwise the first
  label in sorted order; otherwise `None`.

### Case prompt text (non-jsonl input)

`_load_case_prompt` (generate_dashboard.py:91-111) separately reads the
agent-visible `prompt` field from `verticals/<vertical>/cases/<case_id>.json`
(never `evaluator_only`), truncated to `CASE_PROMPT_MAX_LEN = 90` chars with a
`"..."` suffix when truncated. Missing file, missing field, or non-string
`prompt` all resolve to `None`, not an error.

## Chart / section specifications

Source: `render_html` and its client-side script (generate_dashboard.py:
roughly 620-930).

1. **Playground/walkthrough card** — rendered only when
   `include_synthetic_walkthrough=True`; sourced from
   `DATA.synthetic_walkthrough` (built by `_build_synthetic_walkthrough`,
   generate_dashboard.py:237-301), which runs the offline demo harness and
   reports a fixed 8-check list (reset, read, mutation, invalid input,
   disallowed action, duplicate, injected failure, privacy). Not driven by
   the jsonl payload.
2. **60-case evaluation readiness table** — sourced entirely from the static
   `EVALUATION_READINESS` list (generate_dashboard.py:69-78): 8 fixed rows
   (H1/H2/H4/H5/E1/E2/E3/E5), fixed case counts (Healthcare 32, E-commerce
   28 total), every row always shown as `"READY OFFLINE"`. Independent of
   jsonl content — do not read this table as reflecting actual run results.
3. **Framework evidence availability cards** — one per
   `KNOWN_FRAMEWORK_ORDER` entry, showing `evidence_status` / `evidence_kind`
   / `evidence_note` from `FRAMEWORK_EVIDENCE`, plus a live count of
   sanitized rows for the currently selected label.
4. **Per-case technical validation matrix** — rows are case IDs for the
   selected label (`cases_by_label`), columns are frameworks. Cell state,
   computed client-side by `bucket(r)` (generate_dashboard.py JS,
   ~line 662-667):
   - `"not available"` — framework not in `PUBLIC_EVIDENCE_FRAMEWORKS`.
   - `"·"` — no matching run for that case/framework/label.
   - otherwise, one of `TAG` (generate_dashboard.py JS, ~line 647):
     `pass → "MATCH"`, `fail → "MISMATCH"`, `error → "ERROR"`,
     `unknown → "UNKNOWN"`, selected by:
     - `runtime_status not in {"unknown", "completed"}` → `"error"`
     - else `final_state_verdict == "correct"` → `"pass"`
     - else `final_state_verdict == "incorrect"` → `"fail"`
     - else → `"unknown"`
   - A warning-flag icon renders additionally whenever `schema_valid ===
     false` for that cell.
5. **Drawer detail panel** — on cell click, shows the sanitized trace steps
   (dot colored by `outcome === "ok"`) and the aggregate final-state verdict
   only. Underlying state values, hashes, and evaluator payloads are never
   shown — this is enforced by the same private-field allowlist covering the
   input contract above.

## Non-goals (restated from the module docstring and README)

This dashboard is illustrative synthetic technical validation. It is never a
benchmark score, framework ranking, or live E5 result. `results/dashboard.html`
is generated and gitignored, not checked into the repository.

## Enforcement

`tests/test_generate_dashboard.py` pins: the dedup rule, the
`final_state_verdict` mapping, private-field exclusion from the rendered HTML,
framework cards showing only `evidence_status` (no score-shaped strings), and
the fixed 60-case readiness table. It additionally pins (added alongside this
freeze): `KNOWN_FRAMEWORK_ORDER` / `FRAMEWORK_COLORS` values, `CASE_PROMPT_MAX_LEN`
truncation behavior, and `LABEL_PREFERENCE` default-label selection. A change
to any frozen value in this doc must update the corresponding test.
