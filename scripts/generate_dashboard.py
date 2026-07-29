#!/usr/bin/env python3
"""Generate the public WS3 retail Run Console.

Pulls the latest result per (case_id, framework, experiment_label) from
results/metrics/<vertical>_results.jsonl via adapter.result_writer and
writes a self-contained results/dashboard.html. This is a public,
illustrative view of synthetic technical validation, never benchmark
scores or a framework ranking.

The payload is deliberately allowlisted. It contains only sanitized tool
trace summaries and an aggregate final-state verdict; raw arguments,
private traces, hashes, evaluator payloads, actual state, and gold state
are never serialized into the HTML.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.result_writer import default_result_path

OUTPUT_PATH = ROOT / "results" / "dashboard.html"

FRAMEWORK_LABELS = {
    "langgraph": "LangGraph",
    "openai_agents_sdk": "OpenAI Agents SDK",
    "crewai": "CrewAI",
}
FRAMEWORK_COLORS = {
    "langgraph": "#3B4CC0",
    "openai_agents_sdk": "#0E8F8F",
    "crewai": "#B0476A",
}
DEFAULT_FRAMEWORK_COLOR = "#5A6472"
KNOWN_FRAMEWORK_ORDER = ["langgraph", "openai_agents_sdk", "crewai"]

LABEL_PREFERENCE = ["technical_smoke", "pilot", "benchmark"]

CASE_PROMPT_MAX_LEN = 90

FRAMEWORK_EVIDENCE = {
    "langgraph": {
        "status": "available",
        "kind": "actual wrapper evidence",
        "note": "Synthetic technical validation only; not a benchmark score.",
    },
    "openai_agents_sdk": {
        "status": "not_available",
        "kind": "not available",
        "note": "No public wrapper evidence is available.",
    },
    "crewai": {
        "status": "not_available",
        "kind": "not available",
        "note": "No public wrapper evidence is available.",
    },
}
PUBLIC_EVIDENCE_FRAMEWORKS = {
    framework
    for framework, evidence in FRAMEWORK_EVIDENCE.items()
    if evidence["status"] == "available"
}


def _first_present(row: dict, raw: dict, key: str):
    """Prefer a first-class field on the row; fall back to raw_metadata.
    Returns None (never a guessed value) if neither has it."""
    if key in row and row[key] is not None:
        return row[key]
    if key in raw and raw[key] is not None:
        return raw[key]
    return None


def _load_case_prompt(vertical: str, case_id: str) -> str | None:
    """Best-effort, non-gold case label for the matrix/drawer -- reads the
    agent-visible 'prompt' field straight from the case fixture, if present.
    Never touches evaluator_only (see adapter/retail_core/state.py)."""
    path = ROOT / "verticals" / vertical / "cases" / f"{case_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        return None
    if len(prompt) > CASE_PROMPT_MAX_LEN:
        return prompt[: CASE_PROMPT_MAX_LEN - 3] + "..."
    return prompt


def _sanitize_trace(trace) -> list[dict] | None:
    """Return an allowlisted, value-free public trace summary."""
    if trace is None or not isinstance(trace, list):
        return None

    sanitized = []
    for fallback_index, step in enumerate(trace):
        if not isinstance(step, dict):
            continue
        tool_name = step.get("tool_name") or step.get("tool") or "unknown_tool"
        ok = step.get("ok")
        error = step.get("error")
        error_code = step.get("error_code")
        if error_code is None and isinstance(error, dict):
            error_code = error.get("error_type")
        if ok is True:
            outcome = "ok"
        elif error_code:
            outcome = str(error_code)
        elif ok is False:
            outcome = "error"
        else:
            outcome = "unknown"

        index = step.get("index", step.get("sequence_index", fallback_index))
        if not isinstance(index, int):
            index = fallback_index
        state_changed = step.get("state_changed", step.get("mut", False))
        sanitized.append(
            {
                "index": index,
                "tool_name": str(tool_name),
                "outcome": outcome,
                "state_changed": state_changed is True,
            }
        )
    return sanitized


def _final_state_verdict(value) -> str:
    if value is True:
        return "correct"
    if value is False:
        return "incorrect"
    return "not_available"


def _build_run(row: dict) -> dict:
    raw = row.get("raw_metadata") or {}

    experiment_label = _first_present(row, raw, "experiment_label")
    runtime_status = _first_present(row, raw, "runtime_status")
    schema_valid = _first_present(row, raw, "schema_valid")
    final_state_correct = _first_present(row, raw, "final_state_correct")
    trace = _first_present(row, raw, "trace")

    return {
        "case_id": row.get("case_id") or row["task_id"],
        "framework": row["framework"],
        "experiment_label": experiment_label if experiment_label is not None else "unknown",
        "runtime_status": runtime_status if runtime_status is not None else "unknown",
        "schema_valid": schema_valid if isinstance(schema_valid, bool) else None,
        "final_state_verdict": _final_state_verdict(final_state_correct),
        "trace": _sanitize_trace(trace),
    }


def _load_latest_dashboard_results(vertical: str) -> list[dict]:
    """Keep one row per dashboard cell and experiment label.

    ``adapter.result_writer.load_latest_results`` groups by task, which is too
    coarse for benchmark tasks such as E5 that contain multiple case IDs.
    """
    path = default_result_path(vertical)
    latest: dict[tuple[str, str, str], dict] = {}
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            raw = row.get("raw_metadata") or {}
            case_id = row.get("case_id") or row["task_id"]
            label = _first_present(row, raw, "experiment_label") or "unknown"
            latest[(case_id, row["framework"], label)] = row
    return list(latest.values())


def _collect_frameworks() -> list[dict]:
    frameworks = []
    for framework in KNOWN_FRAMEWORK_ORDER:
        evidence = FRAMEWORK_EVIDENCE[framework]
        frameworks.append(
            {
                "id": framework,
                "label": FRAMEWORK_LABELS[framework],
                "color": FRAMEWORK_COLORS.get(framework, DEFAULT_FRAMEWORK_COLOR),
                "evidence_status": evidence["status"],
                "evidence_kind": evidence["kind"],
                "evidence_note": evidence["note"],
            }
        )
    return frameworks


def _collect_cases_by_label(runs: list[dict], vertical: str) -> dict[str, list[dict]]:
    by_label: dict[str, set[str]] = {}
    for r in runs:
        by_label.setdefault(r["experiment_label"], set()).add(r["case_id"])
    return {
        label: [{"id": cid, "name": _load_case_prompt(vertical, cid)} for cid in sorted(case_ids)]
        for label, case_ids in by_label.items()
    }


def _default_label(labels: list[str]) -> str | None:
    for preferred in LABEL_PREFERENCE:
        if preferred in labels:
            return preferred
    return labels[0] if labels else None


def build_payload(vertical: str) -> dict:
    rows = _load_latest_dashboard_results(vertical)
    runs = [
        _build_run(row)
        for row in rows
        if row.get("framework") in PUBLIC_EVIDENCE_FRAMEWORKS
    ]
    labels = sorted({r["experiment_label"] for r in runs})
    return {
        "vertical": vertical,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "disclosure": "ILLUSTRATIVE · SYNTHETIC TECHNICAL VALIDATION · NOT BENCHMARK SCORES",
        "labels": labels,
        "default_label": _default_label(labels),
        "frameworks": _collect_frameworks(),
        "cases_by_label": _collect_cases_by_label(runs, vertical),
        "runs": runs,
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Retail Simulator — Run Console</title>
<style>
  :root {
    --bg: #E7EAF0;
    --surface: #FFFFFF;
    --surface-2: #F4F6F9;
    --ink: #14171C;
    --muted: #5A6472;
    --faint: #8B94A3;
    --line: #D9DEE6;
    --line-strong: #C3CAD5;
    --accent: #3B4CC0;
    --accent-soft: #E9EBFB;

    --ok: #12875A;      --ok-soft: #DBF0E7;
    --fail: #CF3A54;    --fail-soft: #FBE1E7;
    --error: #C25410;   --error-soft: #FAE9DC;
    --leak: #8A34B0;    --leak-soft: #F1E2F8;
    --warn: #B08600;    --warn-soft: #FAF0D2;
    --na: #98A2B1;      --na-soft: #EDF0F4;

    --font-ui: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --font-mono: ui-monospace, "SF Mono", "JetBrains Mono", "Cascadia Code", Menlo, Consolas, monospace;
    --radius: 10px;
    --shadow: 0 1px 2px rgba(20,23,28,.06), 0 8px 24px rgba(20,23,28,.06);
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; }
  body {
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-ui);
    font-size: 14px;
    line-height: 1.45;
    -webkit-font-smoothing: antialiased;
  }
  .mono { font-family: var(--font-mono); }
  .app { display: grid; grid-template-columns: 248px 1fr; min-height: 100vh; }

  /* ---- control rail ---- */
  .rail {
    background: var(--surface);
    border-right: 1px solid var(--line);
    padding: 20px 18px;
    position: sticky; top: 0; align-self: start; height: 100vh;
    overflow-y: auto;
  }
  .brand { display: flex; align-items: baseline; gap: 8px; margin-bottom: 2px; }
  .brand b { font-size: 15px; letter-spacing: -.01em; }
  .brand .v { font-family: var(--font-mono); font-size: 11px; color: var(--faint); }
  .rail .sub { color: var(--muted); font-size: 12px; margin: 0 0 22px; }

  .ctl { margin-bottom: 22px; }
  .ctl > .lbl {
    font-size: 11px; text-transform: uppercase; letter-spacing: .08em;
    color: var(--faint); margin-bottom: 9px; font-weight: 600;
  }
  select {
    width: 100%; font-family: var(--font-mono); font-size: 13px;
    padding: 8px 10px; border: 1px solid var(--line-strong); border-radius: 8px;
    background: var(--surface-2); color: var(--ink); cursor: pointer;
  }
  select:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .fw-toggles { display: flex; flex-direction: column; gap: 7px; }
  .chk {
    display: flex; align-items: center; gap: 9px; cursor: pointer;
    padding: 7px 9px; border: 1px solid var(--line); border-radius: 8px;
    font-family: var(--font-mono); font-size: 12.5px; user-select: none;
    transition: border-color .12s, background .12s;
  }
  .chk:hover { border-color: var(--line-strong); }
  .chk input { accent-color: var(--accent); width: 15px; height: 15px; }
  .chk.off { opacity: .45; }
  .rail-note {
    margin-top: 6px; font-size: 11.5px; color: var(--muted);
    border-top: 1px solid var(--line); padding-top: 14px;
  }
  .rail-note code { font-family: var(--font-mono); color: var(--ink); font-size: 11px; }

  /* ---- main ---- */
  main { padding: 24px 30px 60px; max-width: 1180px; }
  .head { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 22px; flex-wrap: wrap; }
  .head h1 { font-size: 21px; margin: 0 0 4px; letter-spacing: -.015em; }
  .head p { margin: 0; color: var(--muted); font-size: 12.5px; }
  .head .meta { text-align: right; font-family: var(--font-mono); font-size: 11.5px; color: var(--faint); }
  .pill {
    display: inline-block; font-family: var(--font-mono); font-size: 11px;
    padding: 3px 9px; border-radius: 999px; background: var(--accent-soft);
    color: var(--accent); font-weight: 600; letter-spacing: .02em;
  }
  .disclosure {
    margin: 0 0 20px; padding: 11px 14px; border: 1px solid #EBD79A;
    border-radius: 9px; background: var(--warn-soft); color: #735900;
    font-family: var(--font-mono); font-size: 11.5px; font-weight: 700;
    letter-spacing: .03em;
  }

  section { margin-bottom: 30px; }
  .sec-h { display: flex; align-items: baseline; gap: 10px; margin: 0 0 13px; }
  .sec-h h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .09em; color: var(--muted); margin: 0; font-weight: 700; }
  .sec-h .hint { font-size: 12px; color: var(--faint); }

  /* summary cards */
  .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
  .card {
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    padding: 15px 16px; box-shadow: var(--shadow);
  }
  .card .fw { font-family: var(--font-mono); font-size: 12.5px; font-weight: 600; margin-bottom: 12px; display:flex; align-items:center; gap:8px; }
  .card .fw .swatch { width: 9px; height: 9px; border-radius: 2px; }
  .evidence-status { font-family: var(--font-mono); font-size: 16px; font-weight: 700; margin: 3px 0 6px; }
  .evidence-status.available { color: var(--ok); }
  .evidence-status.not_available { color: var(--na); }
  .evidence-note { color: var(--muted); font-size: 12px; min-height: 35px; }
  .kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 12px; }
  .kpi .n { font-family: var(--font-mono); font-size: 20px; font-weight: 600; letter-spacing: -.02em; }
  .kpi .n small { font-size: 12px; color: var(--faint); font-weight: 500; }
  .kpi .k { font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; color: var(--faint); margin-top: 1px; }
  .kpi .u { font-size: 9.5px; color: var(--faint); margin-top: 1px; font-family: var(--font-mono); }
  .kpi .bar { height: 4px; border-radius: 3px; background: var(--surface-2); margin-top: 6px; overflow: hidden; }
  .kpi .bar > i { display: block; height: 100%; border-radius: 3px; }

  /* matrix */
  .matrix-wrap { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }
  table { border-collapse: collapse; width: 100%; }
  thead th {
    font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted);
    font-weight: 600; text-align: left; padding: 12px 14px; border-bottom: 1px solid var(--line);
    background: var(--surface-2);
  }
  thead th.fw { font-family: var(--font-mono); text-transform: none; letter-spacing: 0; text-align: center; }
  tbody td { padding: 9px 14px; border-bottom: 1px solid var(--line); vertical-align: middle; }
  tbody tr:last-child td { border-bottom: none; }
  .case-id { font-family: var(--font-mono); font-size: 11.5px; color: var(--muted); }
  .case-name { font-size: 13px; }
  td.cell { text-align: center; padding: 8px; }

  .chip {
    position: relative; display: inline-flex; flex-direction: column; align-items: center; gap: 2px;
    min-width: 74px; padding: 7px 8px 6px; border-radius: 8px; cursor: pointer;
    border: 1px solid transparent; font-family: var(--font-mono); transition: transform .1s, box-shadow .1s;
  }
  .chip:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(20,23,28,.12); }
  .chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .chip .tag { font-size: 11px; font-weight: 700; letter-spacing: .03em; }
  .chip .code { font-size: 9.5px; opacity: .85; }
  .chip.pass  { background: var(--ok-soft);   color: var(--ok);   border-color: #BEE6D4; }
  .chip.fail  { background: var(--fail-soft); color: var(--fail); border-color: #F3C9D2; }
  .chip.error { background: var(--error-soft);color: var(--error);border-color: #F0D3BC; }
  .chip.leak  { background: var(--leak-soft); color: var(--leak); border-color: #E4C7F0; }
  .chip.unknown { background: var(--na-soft); color: var(--na); border-color: var(--line-strong); }
  .chip .schema-flag {
    position: absolute; top: -5px; right: -5px; width: 0; height: 0;
    border-left: 9px solid transparent; border-top: 9px solid var(--warn);
  }
  .chip .schema-flag::after { content: "!"; position: absolute; top: -9px; left: -4px; font-size: 8px; color: #fff; font-weight: 700; }

  /* failure breakdown */
  .fm-row { display: grid; grid-template-columns: 150px 1fr; align-items: center; gap: 14px; margin-bottom: 10px; }
  .fm-row .fw { font-family: var(--font-mono); font-size: 12px; color: var(--muted); }
  .fm-bar { display: flex; height: 22px; border-radius: 6px; overflow: hidden; border: 1px solid var(--line); background: var(--surface-2); }
  .fm-seg { position: relative; }
  .fm-seg[title]:hover { filter: brightness(1.08); }
  .legend { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 14px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 11px; color: var(--muted); }
  .legend i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }

  /* schema panel */
  .schema-list { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }
  .schema-item { display: grid; grid-template-columns: 130px 130px 1fr; gap: 12px; padding: 11px 16px; border-bottom: 1px solid var(--line); font-family: var(--font-mono); font-size: 12px; align-items: center; }
  .schema-item:last-child { border-bottom: none; }
  .schema-item .warnbadge { color: var(--warn); background: var(--warn-soft); border: 1px solid #EBD79A; padding: 2px 7px; border-radius: 6px; font-size: 10.5px; justify-self: start; }
  .schema-item .warnbadge.na { color: var(--na); background: var(--na-soft); border-color: var(--line-strong); }
  .empty { padding: 26px; text-align: center; color: var(--muted); font-size: 13px; }
  .empty.big { padding: 60px 20px; }

  /* drawer */
  .backdrop { position: fixed; inset: 0; background: rgba(20,23,28,.32); opacity: 0; pointer-events: none; transition: opacity .18s; z-index: 40; }
  .backdrop.on { opacity: 1; pointer-events: auto; }
  .drawer {
    position: fixed; top: 0; right: 0; height: 100vh; width: min(560px, 94vw);
    background: var(--surface); border-left: 1px solid var(--line); box-shadow: -12px 0 40px rgba(20,23,28,.16);
    transform: translateX(100%); transition: transform .22s cubic-bezier(.4,0,.2,1); z-index: 50;
    display: flex; flex-direction: column;
  }
  .drawer.on { transform: translateX(0); }
  .drawer header { padding: 18px 22px 14px; border-bottom: 1px solid var(--line); position: relative; }
  .drawer .close { position: absolute; top: 15px; right: 18px; border: 1px solid var(--line); background: var(--surface-2); border-radius: 7px; width: 30px; height: 30px; cursor: pointer; font-size: 16px; color: var(--muted); }
  .drawer .close:hover { color: var(--ink); }
  .drawer .did { font-family: var(--font-mono); font-size: 11.5px; color: var(--faint); }
  .drawer h3 { margin: 4px 0 10px; font-size: 16px; letter-spacing: -.01em; }
  .verdict { display: inline-flex; align-items: center; gap: 7px; font-family: var(--font-mono); font-size: 12px; padding: 4px 10px; border-radius: 7px; font-weight: 600; }
  .drawer .facts { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 12px; font-family: var(--font-mono); font-size: 11.5px; color: var(--muted); }
  .drawer .facts b { color: var(--ink); font-weight: 600; }
  .drawer .body { padding: 18px 22px 40px; overflow-y: auto; }
  .blk-h { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--faint); font-weight: 700; margin: 20px 0 10px; }
  .blk-h:first-child { margin-top: 0; }

  .trace { display: flex; flex-direction: column; gap: 0; }
  .step { display: grid; grid-template-columns: 26px 1fr; gap: 10px; }
  .step .rail-i { display: flex; flex-direction: column; align-items: center; }
  .step .dot { width: 12px; height: 12px; border-radius: 50%; margin-top: 4px; border: 2px solid; background: var(--surface); }
  .step .line { width: 2px; flex: 1; background: var(--line); margin: 3px 0; }
  .step:last-child .line { display: none; }
  .step .card2 { border: 1px solid var(--line); border-radius: 8px; padding: 9px 11px; margin-bottom: 10px; background: var(--surface); }
  .step .t1 { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .step .tool { font-family: var(--font-mono); font-size: 12.5px; font-weight: 600; }
  .step .res { font-family: var(--font-mono); font-size: 10.5px; padding: 2px 7px; border-radius: 5px; }
  .step .args { font-family: var(--font-mono); font-size: 11px; color: var(--muted); margin-top: 4px; word-break: break-all; }
  .step .mut { font-family: var(--font-mono); font-size: 10px; margin-top: 5px; display: inline-block; padding: 1px 6px; border-radius: 4px; background: var(--accent-soft); color: var(--accent); }
  .dot.ok { border-color: var(--ok); } .res.ok { background: var(--ok-soft); color: var(--ok); }
  .dot.bad { border-color: var(--fail); } .res.bad { background: var(--fail-soft); color: var(--fail); }

  .state-cmp { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .state-box { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
  .state-box .sb-h { font-family: var(--font-mono); font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; padding: 7px 10px; background: var(--surface-2); border-bottom: 1px solid var(--line); color: var(--muted); }
  .state-box pre { margin: 0; padding: 10px; font-family: var(--font-mono); font-size: 11px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
  .state-box.exp .sb-h { color: var(--ok); }
  .diffline { display: block; border-radius: 3px; }
  .diffline.bad { background: var(--fail-soft); }

  @media (max-width: 860px) {
    .app { grid-template-columns: 1fr; }
    .rail { position: static; height: auto; border-right: none; border-bottom: 1px solid var(--line); }
    .cards { grid-template-columns: 1fr; }
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>

<div class="app">
  <aside class="rail">
    <div class="brand"><b>Run Console</b><span class="v">generated</span></div>
    <p class="sub">Retail simulator &middot; public technical evidence</p>

    <div class="ctl">
      <div class="lbl">Experiment label</div>
      <select id="labelSel"></select>
    </div>

    <div class="ctl">
      <div class="lbl">Vertical</div>
      <select id="vertSel"></select>
    </div>

    <div class="ctl">
      <div class="lbl">Frameworks</div>
      <div class="fw-toggles" id="fwToggles"></div>
    </div>

    <div class="rail-note">
      Reads latest row per <code>(case_id, framework, experiment_label)</code>. Labels never mix. Public drill-downs contain only a sanitized trace and aggregate final-state verdict.
    </div>
  </aside>

  <main>
    <div class="head">
      <div>
        <h1>Retail Simulator &mdash; Run Console</h1>
        <p>Illustrative public view of synthetic technical validation evidence.</p>
      </div>
      <div class="meta">
        <span class="pill" id="labelPill">&mdash;</span><br />
        <span id="runCount">&mdash;</span><br />
        <span id="genMeta"></span>
      </div>
    </div>

    <div class="disclosure" id="disclosure"></div>
    <div id="content"><!-- populated --></div>
  </main>
</div>

<div class="backdrop" id="backdrop"></div>
<div class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="Run detail">
  <button class="close" id="drawerClose" aria-label="Close">&times;</button>
  <header id="drawerHead"></header>
  <div class="body" id="drawerBody"></div>
</div>

<script>
/* ------------------------------------------------------------------ *
 * DATA -- generated by scripts/generate_dashboard.py from the latest
 * row per (case_id, framework, experiment_label). The embedded payload is
 * a public allowlist: sanitized trace summaries plus aggregate verdicts.
 * ------------------------------------------------------------------ */
const DATA = __DASHBOARD_DATA_JSON__;

const TAG = { pass:"MATCH", fail:"MISMATCH", error:"ERROR", unknown:"UNKNOWN" };

const fwById = Object.fromEntries(DATA.frameworks.map(f => [f.id, f]));
function runDomKey(caseId, framework, experimentLabel){
  return caseId + "|" + framework + "|" + experimentLabel;
}
const runByDomKey = {};
DATA.runs.forEach(r => {
  runByDomKey[runDomKey(r.case_id, r.framework, r.experiment_label)] = r;
});

const state = { label: DATA.default_label, active: new Set(DATA.frameworks.map(f => f.id)) };

function bucket(r){
  if (r.runtime_status !== "unknown" && r.runtime_status !== "completed") return "error";
  if (r.final_state_verdict === "correct") return "pass";
  if (r.final_state_verdict === "incorrect") return "fail";
  return "unknown";
}

function activeRuns(){
  return DATA.runs.filter(r => r.experiment_label === state.label && state.active.has(r.framework));
}
function esc(s){
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

// ---- control rail: label + vertical selects ----
const labelSel = document.getElementById("labelSel");
DATA.labels.forEach(l => {
  const opt = document.createElement("option");
  opt.value = l; opt.textContent = l;
  labelSel.appendChild(opt);
});
labelSel.value = state.label || "";
labelSel.addEventListener("change", e => {
  state.label = e.target.value;
  document.getElementById("labelPill").textContent = state.label;
  render();
});

const vertSel = document.getElementById("vertSel");
const vopt = document.createElement("option");
vopt.value = DATA.vertical; vopt.textContent = DATA.vertical;
vertSel.appendChild(vopt);

// ---- control rail: framework toggles ----
const fwToggles = document.getElementById("fwToggles");
DATA.frameworks.forEach(f => {
  const el = document.createElement("label");
  el.className = "chk";
  el.innerHTML = `<input type="checkbox" checked data-fw="${f.id}"><span style="width:9px;height:9px;border-radius:2px;background:${f.color};display:inline-block"></span>${esc(f.label)}`;
  el.querySelector("input").addEventListener("change", e => {
    e.target.checked ? state.active.add(f.id) : state.active.delete(f.id);
    el.classList.toggle("off", !e.target.checked);
    render();
  });
  fwToggles.appendChild(el);
});

document.getElementById("labelPill").textContent = state.label || "none";
document.getElementById("genMeta").textContent = `${DATA.vertical} · generated ${DATA.generated_at}`;
document.getElementById("disclosure").textContent = DATA.disclosure;

function render(){
  const runs = activeRuns();
  document.getElementById("runCount").textContent = runs.length + " public evidence rows";
  const content = document.getElementById("content");
  const cases = DATA.cases_by_label[state.label] || [];

  let html = "";

  // 1. evidence availability -- deliberately not a score or ranking.
  html += `<section><div class="sec-h"><h2>Framework evidence availability</h2><span class="hint">availability only &middot; no simulated ranking</span></div><div class="cards">`;
  DATA.frameworks.filter(f => state.active.has(f.id)).forEach(f => {
    const evidenceCount = runs.filter(r => r.framework === f.id).length;
    const countNote = f.evidence_status === "available"
      ? `${evidenceCount} sanitized row${evidenceCount === 1 ? "" : "s"} for this label`
      : "No result rows are published";
    html += `<div class="card">
      <div class="fw"><span class="swatch" style="background:${f.color}"></span>${esc(f.label)}</div>
      <div class="evidence-status ${esc(f.evidence_status)}">${esc(f.evidence_kind)}</div>
      <div class="evidence-note">${esc(f.evidence_note)}<br>${esc(countNote)}</div>
    </div>`;
  });
  html += `</div></section>`;

  if (!DATA.labels.length || !cases.length){
    html += `<div class="matrix-wrap"><div class="empty big">No public evidence rows are available for <span class="mono">${esc(state.label || DATA.vertical)}</span>.<br><span style="font-size:12px">Unavailable evidence is shown explicitly and is never replaced with simulated results.</span></div></div>`;
    content.innerHTML = html;
    return;
  }

  // 2. per-case aggregate verdicts
  html += `<section><div class="sec-h"><h2>Per-case technical validation</h2><span class="hint">click available cells for sanitized trace + aggregate final-state verdict</span></div><div class="matrix-wrap"><table><thead><tr><th>Case</th>`;
  DATA.frameworks.filter(f=>state.active.has(f.id)).forEach(f => html += `<th class="fw">${esc(f.label)}</th>`);
  html += `</tr></thead><tbody>`;
  cases.forEach(c => {
    html += `<tr><td><div class="case-name">${c.name ? esc(c.name) : ""}</div><div class="case-id">${esc(c.id)}</div></td>`;
    DATA.frameworks.filter(f=>state.active.has(f.id)).forEach(f => {
      if (f.evidence_status !== "available"){
        html += `<td class="cell"><span style="color:var(--faint);font-family:var(--font-mono);font-size:10.5px">not available</span></td>`;
        return;
      }
      const lookupKey = runDomKey(c.id, f.id, state.label);
      const r = runByDomKey[lookupKey];
      if (!r){
        html += `<td class="cell"><span style="color:var(--faint);font-family:var(--font-mono);font-size:11px">&middot;</span></td>`;
        return;
      }
      const b = bucket(r);
      const domKey = runDomKey(r.case_id, r.framework, r.experiment_label);
      html += `<td class="cell"><button class="chip ${b}" data-run="${esc(domKey)}" aria-label="${esc(c.id)} ${esc(f.label)} ${esc(r.final_state_verdict)}">
        ${r.schema_valid === false ? '<span class="schema-flag"></span>' : ''}
        <span class="tag">${TAG[b]}</span><span class="code">${esc(r.final_state_verdict)}</span></button></td>`;
    });
    html += `</tr>`;
  });
  html += `</tbody></table></div></section>`;

  content.innerHTML = html;
  content.querySelectorAll(".chip").forEach(btn => btn.addEventListener("click", () => openDrawer(btn.dataset.run)));
}

/* ---- drawer ---- */
const drawer = document.getElementById("drawer");
const backdrop = document.getElementById("backdrop");
function closeDrawer(){ drawer.classList.remove("on"); backdrop.classList.remove("on"); }
document.getElementById("drawerClose").addEventListener("click", closeDrawer);
backdrop.addEventListener("click", closeDrawer);
document.addEventListener("keydown", e => { if(e.key==="Escape") closeDrawer(); });

function openDrawer(domKey){
  const r = runByDomKey[domKey]; if(!r) return;
  const cases = DATA.cases_by_label[r.experiment_label] || [];
  const c = cases.find(x => x.id === r.case_id);
  const f = fwById[r.framework] || { label: r.framework, color: "#5A6472" };
  const b = bucket(r);
  const verdictColor = { pass:"var(--ok)", fail:"var(--fail)", error:"var(--error)", unknown:"var(--na)" }[b];
  const verdictBg    = { pass:"var(--ok-soft)", fail:"var(--fail-soft)", error:"var(--error-soft)", unknown:"var(--na-soft)" }[b];

  document.getElementById("drawerHead").innerHTML = `
    <button class="close" id="drawerClose2" aria-label="Close">&times;</button>
    <div class="did">${esc(r.experiment_label)} &middot; sanitized public detail</div>
    <h3>${c && c.name ? esc(c.name) : esc(r.case_id)}</h3>
    <span class="verdict" style="color:${verdictColor};background:${verdictBg}">${TAG[b]} &middot; ${esc(r.final_state_verdict)}</span>
    <div class="facts">
      <span><b>${esc(f.label)}</b></span>
      <span>case <b>${esc(r.case_id)}</b></span>
      <span>status <b>${esc(r.runtime_status)}</b></span>
      <span>schema <b>${r.schema_valid === true ? "valid" : r.schema_valid === false ? "INVALID" : "unknown"}</b></span>
      <span>final-state verdict <b>${esc(r.final_state_verdict)}</b></span>
    </div>`;
  document.getElementById("drawerHead").querySelector("#drawerClose2").addEventListener("click", closeDrawer);

  let body = "";
  body += `<div class="blk-h">Sanitized tool trace</div>`;
  if (r.trace === null){
    body += `<div class="empty" style="border:1px dashed var(--line);border-radius:8px">No public trace summary is available.</div>`;
  } else if (!r.trace.length){
    body += `<div class="empty" style="border:1px dashed var(--line);border-radius:8px">No tool calls &mdash; agent answered without touching the simulator.</div>`;
  } else {
    body += `<div class="trace">`;
    r.trace.forEach((s,i) => {
      const cls = s.outcome === "ok" ? "ok" : "bad";
      const mutated = s.state_changed === true;
      const idx = (s.index != null ? s.index : i) + 1;
      body += `<div class="step"><div class="rail-i"><span class="dot ${cls}"></span><span class="line"></span></div>
        <div class="card2"><div class="t1"><span class="tool">${idx}. ${esc(s.tool_name)}</span><span class="res ${cls}">${esc(s.outcome)}</span></div>
        ${mutated ? '<span class="mut">state changed</span>' : ''}</div></div>`;
    });
    body += `</div>`;
  }

  body += `<div class="blk-h">Aggregate final-state verdict</div>`;
  body += `<div class="card2" style="border:1px solid var(--line);border-left:3px solid ${verdictColor};border-radius:8px;padding:12px 13px">
    <span class="verdict" style="color:${verdictColor};background:${verdictBg}">${esc(r.final_state_verdict)}</span>
    <div style="color:var(--muted);font-size:12px;margin-top:8px">Underlying state values are intentionally not included in this public dashboard.</div>
  </div>`;

  document.getElementById("drawerBody").innerHTML = body;
  drawer.classList.add("on"); backdrop.classList.add("on");
}

render();
</script>
</body>
</html>
"""


def render_html(payload: dict) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__DASHBOARD_DATA_JSON__", payload_json)


def build(vertical: str) -> str:
    payload = build_payload(vertical)
    return render_html(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vertical", default="retail", help="vertical whose results/metrics/<vertical>_results.jsonl to render (default: retail)")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build(args.vertical), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
