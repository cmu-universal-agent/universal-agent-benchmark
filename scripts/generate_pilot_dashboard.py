#!/usr/bin/env python3
"""WS4/WS5 controlled-pilot dashboard.

Without inputs this renders the frozen run-matrix placeholder. With a local
privacy-confirmed aggregate and matching freeze record it renders a candidate
results view. Private source files and generated HTML remain ignored.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from html import escape
from math import isfinite
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_dashboard import FRAMEWORK_COLORS, FRAMEWORK_LABELS, KNOWN_FRAMEWORK_ORDER

OUTPUT_PATH = ROOT / "results" / "pilot_dashboard.html"
REPORT_PATH = ROOT / "docs" / "experiment_report_skeleton.md"

# Frozen per docs/representative_case_ids.md and docs/experiment_report_skeleton.md.
WS4_TASKS = [
    {"task_id": "H1", "vertical": "Healthcare", "title": "Medical QA", "score_label": "Evaluator mean", "cases": 8, "representative_case_id": "H1-REVIEW-001"},
    {"task_id": "H2", "vertical": "Healthcare", "title": "Triage safety", "score_label": "Evaluator mean", "cases": 8, "representative_case_id": "H2-REVIEW-001"},
    {"task_id": "H4", "vertical": "Healthcare", "title": "Clinical extraction", "score_label": "Mean set-F1", "cases": 8, "representative_case_id": "H4-REVIEW-001"},
    {"task_id": "H5", "vertical": "Healthcare", "title": "Boundary handling", "score_label": "Rubric mean", "cases": 8, "representative_case_id": "H5-REVIEW-001"},
    {"task_id": "E1", "vertical": "E-commerce", "title": "Trend judgment", "score_label": "Evaluator mean", "cases": 8, "representative_case_id": "E1-REVIEW-001"},
    {"task_id": "E2", "vertical": "E-commerce", "title": "Recommendation", "score_label": "Evaluator mean", "cases": 8, "representative_case_id": "E2-REVIEW-001"},
    {"task_id": "E3", "vertical": "E-commerce", "title": "Policy decision", "score_label": "Evaluator mean", "cases": 8, "representative_case_id": "E3-REVIEW-001"},
    {"task_id": "E5", "vertical": "E-commerce", "title": "Stateful tool use", "score_label": "Final-state pass rate", "cases": 4, "representative_case_id": "E5-001"},
]
FRAMEWORKS_PER_TASK = 3
REPEATS_PER_REPRESENTATIVE_CASE = 2  # additional targeted repeats, one representative case per task
EXPECTED_RESULTS_PER_PAIR = {
    task["task_id"]: task["cases"] + REPEATS_PER_REPRESENTATIVE_CASE
    for task in WS4_TASKS
}
REPRESENTATIVE_CASE_IDS = {
    task["task_id"]: task["representative_case_id"] for task in WS4_TASKS
}

AGGREGATE_TOP_LEVEL_FIELDS = {
    "schema_version", "generated_at", "experiment_id", "status",
    "claim_boundary", "invalid_e5_frameworks", "rows", "targeted_repeats",
}
AGGREGATE_ROW_FIELDS = {
    "task_id", "framework", "n", "process_success", "schema_valid", "scored_n",
    "content_pass", "mean_score", "e5_pass", "e5_fail", "e5_error",
    "e5_sweep_valid", "h5_pending", "avg_latency_seconds", "input_tokens",
    "output_tokens", "estimated_cost_usd",
}
TARGETED_REPEAT_FIELDS = {
    "case_id", "task_id", "framework", "observations", "complete", "stable",
}
INTEGER_ROW_FIELDS = {
    "n", "process_success", "schema_valid", "scored_n", "content_pass",
    "e5_pass", "e5_fail", "e5_error", "h5_pending",
}
OPTIONAL_NUMBER_ROW_FIELDS = {
    "mean_score", "avg_latency_seconds", "input_tokens", "output_tokens",
    "estimated_cost_usd",
}


def _gate_status() -> str:
    prefix = "- Gate status: `"
    for line in REPORT_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix) and line.endswith("`"):
            return line[len(prefix) : -1]
    raise ValueError(f"Gate status not found in {REPORT_PATH.relative_to(ROOT)}")


def _task_row(task: dict) -> dict:
    preflights = FRAMEWORKS_PER_TASK
    main_runs = task["cases"] * FRAMEWORKS_PER_TASK
    repeats = REPEATS_PER_REPRESENTATIVE_CASE * FRAMEWORKS_PER_TASK
    return {
        "task_id": task["task_id"],
        "vertical": task["vertical"],
        "title": task["title"],
        "score_label": task["score_label"],
        "cases": task["cases"],
        "representative_case_id": task["representative_case_id"],
        "preflights": preflights,
        "main_runs": main_runs,
        "repeats": repeats,
        "controlled_total": main_runs + repeats,
    }


def _validate_aggregate(aggregate: dict, freeze: dict) -> None:
    if set(aggregate) != AGGREGATE_TOP_LEVEL_FIELDS:
        raise ValueError("aggregate top-level fields do not match the public allowlist")
    if not all(isinstance(value, list) for value in (aggregate["rows"], aggregate["targeted_repeats"])):
        raise ValueError("aggregate rows and targeted repeats must be lists")
    if any(
        not isinstance(row, dict) or set(row) != AGGREGATE_ROW_FIELDS
        for row in aggregate["rows"]
    ):
        raise ValueError("aggregate row fields do not match the public allowlist")
    if any(
        not isinstance(row, dict) or set(row) != TARGETED_REPEAT_FIELDS
        for row in aggregate["targeted_repeats"]
    ):
        raise ValueError("targeted-repeat fields do not match the public allowlist")
    if any(
        any(type(row[field]) is not int for field in INTEGER_ROW_FIELDS)
        or any(
            row[field] is not None and type(row[field]) not in (int, float)
            for field in OPTIONAL_NUMBER_ROW_FIELDS
        )
        or (row["e5_sweep_valid"] is not None and type(row["e5_sweep_valid"]) is not bool)
        for row in aggregate["rows"]
    ):
        raise ValueError("aggregate result fields have invalid types")
    if any(
        type(row["complete"]) is not bool or type(row["stable"]) is not bool
        for row in aggregate["targeted_repeats"]
    ):
        raise ValueError("targeted-repeat status fields must be boolean")
    if (
        type(aggregate["invalid_e5_frameworks"]) is not list
        or any(type(framework) is not str for framework in aggregate["invalid_e5_frameworks"])
    ):
        raise ValueError("invalid_e5_frameworks must be a list of framework names")
    if freeze.get("experiment_id") != aggregate.get("experiment_id"):
        raise ValueError("aggregate and freeze experiment IDs differ")
    if "scoring_complete" not in str(freeze.get("status", "")):
        raise ValueError("freeze record does not confirm scoring completion")
    if freeze.get("owner_confirmations", {}).get("privacy_boundary_confirmed") is not True:
        raise ValueError("privacy boundary is not confirmed")
    privacy = freeze.get("privacy", {})
    if (
        type(privacy.get("aggregate_forbidden_field_matches")) is not int
        or privacy["aggregate_forbidden_field_matches"] != 0
    ):
        raise ValueError("aggregate privacy scan did not pass")
    if type(privacy.get("public_release_authorized")) is not bool:
        raise ValueError("public_release_authorized must be boolean")
    expected_pairs = {
        (task["task_id"], framework)
        for task in WS4_TASKS for framework in KNOWN_FRAMEWORK_ORDER
    }
    row_pairs = [(row["task_id"], row["framework"]) for row in aggregate["rows"]]
    repeat_pairs = [
        (row["task_id"], row["framework"]) for row in aggregate["targeted_repeats"]
    ]
    if set(row_pairs) != expected_pairs or len(row_pairs) != len(expected_pairs):
        raise ValueError("aggregate task/framework combinations are incomplete or duplicated")
    if set(repeat_pairs) != expected_pairs or len(repeat_pairs) != len(expected_pairs):
        raise ValueError("targeted-repeat task/framework combinations are incomplete or duplicated")

    for row in aggregate["rows"]:
        task_id = row["task_id"]
        expected_n = EXPECTED_RESULTS_PER_PAIR[task_id]
        if row["n"] != expected_n:
            raise ValueError(f"{task_id} rows must use frozen n={expected_n}")
        if any(row[field] < 0 for field in INTEGER_ROW_FIELDS):
            raise ValueError("aggregate integer result fields must be non-negative")
        if not 0 <= row["schema_valid"] <= row["process_success"] <= row["n"]:
            raise ValueError("process and schema counts are inconsistent with n")
        if not 0 <= row["content_pass"] <= row["scored_n"] <= row["n"]:
            raise ValueError("content pass and scored counts are inconsistent with n")
        for field in OPTIONAL_NUMBER_ROW_FIELDS:
            value = row[field]
            if value is not None and (not isfinite(value) or value < 0):
                raise ValueError("aggregate numeric result fields must be finite and non-negative")
        if row["h5_pending"] != 0:
            raise ValueError("scoring-complete aggregate must have h5_pending=0")

        if task_id == "E5":
            if row["scored_n"] != 0 or row["content_pass"] != 0 or row["mean_score"] is not None:
                raise ValueError("E5 rows must use only E5 verdict fields")
            if type(row["e5_sweep_valid"]) is not bool:
                raise ValueError("E5 rows must declare e5_sweep_valid")
            if row["e5_pass"] + row["e5_fail"] + row["e5_error"] != row["n"]:
                raise ValueError("E5 verdict counts must sum to n")
            if row["e5_pass"] + row["e5_fail"] != row["process_success"]:
                raise ValueError("E5 pass/fail counts must match process_success")
            expected_valid = row["e5_error"] / row["n"] <= 0.05
            if row["e5_sweep_valid"] is not expected_valid:
                raise ValueError("E5 sweep validity contradicts the frozen error threshold")
        else:
            if row["scored_n"] != row["n"]:
                raise ValueError("non-E5 scoring-complete rows must score all n results")
            if row["mean_score"] is None or not 0 <= row["mean_score"] <= 1:
                raise ValueError("non-E5 mean_score must be between 0 and 1")
            if any(row[field] != 0 for field in ("e5_pass", "e5_fail", "e5_error")):
                raise ValueError("non-E5 rows cannot contain E5 verdict counts")
            if row["e5_sweep_valid"] is not None:
                raise ValueError("non-E5 rows cannot declare e5_sweep_valid")

    declared_invalid = aggregate["invalid_e5_frameworks"]
    if (
        len(declared_invalid) != len(set(declared_invalid))
        or any(framework not in KNOWN_FRAMEWORK_ORDER for framework in declared_invalid)
    ):
        raise ValueError("invalid_e5_frameworks contains unknown or duplicate frameworks")
    expected_invalid = {
        row["framework"]
        for row in aggregate["rows"]
        if row["task_id"] == "E5" and row["e5_sweep_valid"] is False
    }
    if set(declared_invalid) != expected_invalid:
        raise ValueError("invalid_e5_frameworks contradicts E5 row validity")

    for row in aggregate["targeted_repeats"]:
        if row["case_id"] != REPRESENTATIVE_CASE_IDS[row["task_id"]]:
            raise ValueError("targeted-repeat case_id does not match the frozen representative ID")
        if type(row["observations"]) is not list or len(row["observations"]) != 3:
            raise ValueError("each targeted-repeat row must contain three observations")
    if not all(row["complete"] for row in aggregate["targeted_repeats"]):
        raise ValueError("all 24 targeted-repeat rows must be complete")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload(aggregate: dict | None = None, freeze: dict | None = None) -> dict:
    tasks = [_task_row(task) for task in WS4_TASKS]
    frameworks = [
        {"id": fw, "label": FRAMEWORK_LABELS[fw], "color": FRAMEWORK_COLORS[fw]}
        for fw in KNOWN_FRAMEWORK_ORDER
    ]
    totals = {
        "cases": sum(t["cases"] for t in tasks),
        "preflights": sum(t["preflights"] for t in tasks),
        "main_runs": sum(t["main_runs"] for t in tasks),
        "repeats": sum(t["repeats"] for t in tasks),
        "controlled_total": sum(t["controlled_total"] for t in tasks),
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "gate_status": _gate_status(),
        "frameworks": frameworks,
        "tasks": tasks,
        "totals": totals,
        "aggregate": None,
    }
    if aggregate is not None:
        if freeze is None:
            raise ValueError("freeze confirmation is required with an aggregate")
        _validate_aggregate(aggregate, freeze)
        payload["aggregate"] = {
            "status": freeze["status"],
            "claim_boundary": aggregate["claim_boundary"],
            "public_release_authorized": freeze["privacy"]["public_release_authorized"],
            "invalid_e5_frameworks": aggregate["invalid_e5_frameworks"],
            "rows": aggregate["rows"],
            "targeted_repeats": aggregate["targeted_repeats"],
        }
    return payload


def _task_rows_html(payload: dict) -> str:
    html_rows = []
    for task in payload["tasks"]:
        if payload["aggregate"] is None:
            status_cells = "".join(
                f'<td class="cell pending">pending</td>' for _ in payload["frameworks"]
            )
        else:
            aggregate_rows = payload["aggregate"]["rows"]
            status_cells = "".join(
                '<td class="cell complete">complete</td>'
                if next(
                    r for r in aggregate_rows
                    if r["task_id"] == task["task_id"] and r["framework"] == fw["id"]
                )["process_success"] == task["controlled_total"] // FRAMEWORKS_PER_TASK
                else '<td class="cell error">error</td>'
                for fw in payload["frameworks"]
            )
        html_rows.append(
            f"<tr><td class=\"mono\">{task['task_id']}</td>"
            f"<td>{task['cases']}</td>"
            f"<td>{task['preflights']}</td>"
            f"<td>{task['main_runs']}</td>"
            f"<td class=\"mono\">{task['representative_case_id']}</td>"
            f"<td>{task['repeats']}</td>"
            f"<td>{task['controlled_total']}</td>"
            f"{status_cells}</tr>"
        )
    return "\n".join(html_rows)


def _framework_headers_html(payload: dict) -> str:
    return "".join(
        f'<th class="mono" style="color:{fw["color"]}">{fw["label"]}</th>'
        for fw in payload["frameworks"]
    )


def _control_rail_html(payload: dict) -> str:
    disabled = "" if payload["aggregate"] is not None else " disabled"
    task_options = "".join(
        f'<option value="{task["task_id"]}" data-vertical="{task["vertical"]}">'
        f'{task["task_id"]} · {task["title"]}</option>'
        for task in payload["tasks"]
    )
    toggles = "".join(
        f'<label class="framework-toggle"><input type="checkbox" data-framework="{fw["id"]}" checked{disabled}>'
        f'<span style="background:{fw["color"]}"></span>{fw["label"]}</label>'
        for fw in payload["frameworks"]
    )
    return f"""
      <div class="control"><label for="vertical-filter">Vertical</label>
        <select id="vertical-filter"{disabled}><option value="all">All verticals</option><option>Healthcare</option><option>E-commerce</option></select></div>
      <div class="control"><label for="task-filter">Task</label><select id="task-filter"{disabled}>{task_options}</select></div>
      <div class="control"><label for="metric-filter">Comparison metric</label><select id="metric-filter"{disabled}>
        <option value="task_result">Primary evaluator score</option><option value="process_success">Process success</option>
        <option value="schema_valid">Schema valid</option><option value="avg_latency_seconds">Average latency</option>
        <option value="estimated_cost_usd">Estimated cost</option></select></div>
      <div class="control"><span class="control-label">Frameworks</span><div class="framework-toggles">{toggles}</div></div>
    """


def _overview_html(payload: dict) -> str:
    totals = payload["totals"]
    cards = (
        (totals["cases"], "frozen cases"),
        (totals["controlled_total"], "formal result runs"),
        (totals["preflights"], "formal preflights"),
        (len(payload["frameworks"]), "frameworks"),
    )
    return "".join(
        f'<div class="summary-card"><strong>{value}</strong><span>{label}</span></div>'
        for value, label in cards
    )


def _figure_placeholders_html(payload: dict) -> str:
    bars = "".join(
        f'<div class="bar-row"><span class="mono">{fw["label"]}</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:0%;background:{fw["color"]}"></div></div>'
        f'<span class="mono faint">no data</span></div>'
        for fw in payload["frameworks"]
    )
    return f"""
    <section>
      <h2>Figures (placeholder)</h2>
      <p class="hint">Populated once main-pilot and repeat runs exist; zero-width bars are structural only, not a score of zero.</p>
      <div class="card">
        <div class="card-title">Planned logical runs per framework (main + repeats + preflights)</div>
        {bars}
      </div>
    </section>
    """


def _metric(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _primary_score(row: dict) -> tuple[str, str]:
    if row["task_id"] == "E5":
        if not row["e5_sweep_valid"]:
            return "invalid sweep", "invalid"
        return f'{row["e5_pass"] / row["n"]:.1%}', "score"
    return f'{row["mean_score"]:.1%}', "score"


def _suitability_matrix_html(payload: dict) -> str:
    aggregate_rows = payload["aggregate"]["rows"]
    rows = []
    for task in payload["tasks"]:
        scores = []
        for framework in KNOWN_FRAMEWORK_ORDER:
            row = next(
                item for item in aggregate_rows
                if item["task_id"] == task["task_id"] and item["framework"] == framework
            )
            value, css_class = _primary_score(row)
            scores.append(
                f'<td class="framework-cell" data-framework="{framework}">'
                f'<span class="score {css_class}">{value}</span></td>'
            )
        rows.append(
            f'<tr class="matrix-row" data-task="{task["task_id"]}" data-vertical="{task["vertical"]}">'
            f'<td><span class="mono">{task["task_id"]}</span><br><span class="task-name">{task["title"]}</span></td>'
            f'<td>{task["vertical"]}</td><td>{task["score_label"]}</td>{"".join(scores)}</tr>'
        )
    headers = "".join(
        f'<th class="framework-cell" data-framework="{framework}">{FRAMEWORK_LABELS[framework]}</th>'
        for framework in KNOWN_FRAMEWORK_ORDER
    )
    return f"""
    <section>
      <div class="section-head"><h2>Framework suitability matrix</h2><span>task-specific frozen scores · no composite ranking</span></div>
      <div class="table-wrap"><table class="suitability-matrix"><thead><tr><th>Task</th><th>Vertical</th><th>Primary metric</th>{headers}</tr></thead>
        <tbody>{''.join(rows)}</tbody></table></div>
      <p class="hint">Non-E5 cells show the frozen evaluator mean. E5 shows final-state pass rate; an invalid sweep is excluded from cross-framework comparison.</p>
    </section>
    """


def _results_html(payload: dict) -> str:
    aggregate = payload["aggregate"]
    if aggregate is None:
        return _figure_placeholders_html(payload)
    rows = []
    for row in aggregate["rows"]:
        result = (
            f'{row["e5_pass"]} pass / {row["e5_fail"]} fail / {row["e5_error"]} error'
            if row["task_id"] == "E5"
            else f'{row["content_pass"]}/{row["scored_n"]}; mean={_metric(row["mean_score"])}'
        )
        rows.append(
            f'<tr class="result-row" data-task="{row["task_id"]}" data-framework="{row["framework"]}">'
            f'<td class="mono">{row["task_id"]}</td>'
            f'<td>{FRAMEWORK_LABELS[row["framework"]]}</td><td>{row["n"]}</td>'
            f'<td>{row["process_success"]}</td><td>{row["schema_valid"]}</td>'
            f'<td>{result}</td><td>{_metric(row["avg_latency_seconds"], 2)}</td>'
            f'<td>{_metric(row["estimated_cost_usd"], 6)}</td></tr>'
        )
    stable = sum(row["stable"] for row in aggregate["targeted_repeats"])
    release = "authorized" if aggregate["public_release_authorized"] else "not authorized"
    return f"""
    <section>
      <div class="section-head"><h2>Task score comparison</h2><span>select a task and metric in the control rail</span></div>
      <p class="hint">Privacy-reviewed aggregate candidate. Claims approved; public release is {release}. {escape(aggregate['claim_boundary'])}</p>
      <div class="card comparison-card">
        <div class="card-title" id="comparison-title">Task-specific framework comparison</div>
        <div id="comparison-bars" aria-live="polite"></div>
      </div>
    </section>
    {_suitability_matrix_html(payload)}
    <section>
      <div class="section-head"><h2>Operational detail</h2><span>filtered by the same controls</span></div>
      <div class="table-wrap"><table><thead><tr><th>Task</th><th>Framework</th><th>N</th><th>Process success</th>
        <th>Schema valid</th><th>Task-specific result</th><th>Avg latency (s)</th><th>Est. cost (USD)</th>
      </tr></thead><tbody>{''.join(rows)}</tbody></table></div>
      <p class="hint">Targeted-repeat stability: {stable}/24 complete rows stable. Invalid E5 sweep(s): {escape(', '.join(aggregate['invalid_e5_frameworks']) or 'none')}.</p>
    </section>
    """


def _interaction_script(payload: dict) -> str:
    aggregate = payload["aggregate"]
    if aggregate is None:
        return ""
    data = json.dumps(
        {
            "rows": aggregate["rows"],
            "labels": FRAMEWORK_LABELS,
            "colors": FRAMEWORK_COLORS,
            "taskVerticals": {task["task_id"]: task["vertical"] for task in payload["tasks"]},
        },
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""
<script id="aggregate-data" type="application/json">{data}</script>
<script>
(() => {{
  const data = JSON.parse(document.getElementById("aggregate-data").textContent);
  const vertical = document.getElementById("vertical-filter");
  const task = document.getElementById("task-filter");
  const metric = document.getElementById("metric-filter");
  const toggles = [...document.querySelectorAll(".framework-toggle input")];
  const bars = document.getElementById("comparison-bars");
  const title = document.getElementById("comparison-title");

  const metricValue = (row) => {{
    if (metric.value === "task_result") {{
      if (row.task_id === "E5" && row.e5_sweep_valid === false) return {{value: null, label: "invalid sweep — not comparable", kind: "invalid"}};
      if (row.task_id === "E5") {{
        const value = row.n ? row.e5_pass / row.n : 0;
        return {{value, label: `${{(value * 100).toFixed(1)}}% (${{row.e5_pass}}/${{row.n}})`}};
      }}
      return {{value: row.mean_score, label: `${{(row.mean_score * 100).toFixed(1)}}% mean`}};
    }}
    if (metric.value === "process_success" || metric.value === "schema_valid") {{
      const value = row.n ? row[metric.value] / row.n : 0;
      return {{value, label: `${{(value * 100).toFixed(1)}}% (${{row[metric.value]}}/${{row.n}})`}};
    }}
    const value = row[metric.value];
    if (value === null) return {{value: null, label: "n/a", kind: "unavailable"}};
    const label = metric.value === "avg_latency_seconds" ? `${{value.toFixed(2)}} s` : `$${{value.toFixed(6)}}`;
    return {{value, label}};
  }};

  const render = () => {{
    const active = new Set(toggles.filter((toggle) => toggle.checked).map((toggle) => toggle.dataset.framework));
    document.querySelectorAll(".result-row").forEach((row) => {{
      row.hidden = row.dataset.task !== task.value || !active.has(row.dataset.framework);
    }});
    document.querySelectorAll(".matrix-row").forEach((row) => {{
      row.hidden = vertical.value !== "all" && row.dataset.vertical !== vertical.value;
    }});
    document.querySelectorAll(".framework-cell").forEach((cell) => {{
      cell.hidden = !active.has(cell.dataset.framework);
    }});
    const selected = data.rows.filter((row) => row.task_id === task.value && active.has(row.framework));
    if (!selected.length) {{
      title.textContent = `${{task.value}} · no framework selected`;
      bars.innerHTML = '<p class="empty">Select at least one framework.</p>';
      return;
    }}
    const values = selected.map(metricValue);
    const relativeMetric = metric.value === "avg_latency_seconds" || metric.value === "estimated_cost_usd";
    const max = relativeMetric ? Math.max(...values.map((item) => item.value || 0), 1e-12) : 1;
    title.textContent = `${{task.value}} · ${{metric.options[metric.selectedIndex].text}}`;
    bars.innerHTML = selected.map((row, index) => {{
      const item = values[index];
      const width = item.value === null ? 0 : Math.max(0, Math.min(100, item.value / max * 100));
      const state = item.kind ? ` ${{item.kind}}` : "";
      return `<div class="comparison-row${{state}}"><span class="mono">${{data.labels[row.framework]}}</span>` +
        `<div class="bar-track"><div class="bar-fill" style="width:${{width}}%;background:${{data.colors[row.framework]}}"></div></div>` +
        `<strong class="mono">${{item.label}}</strong></div>`;
    }}).join("");
  }};

  const syncTasks = () => {{
    const eligible = [...task.options].filter((option) => vertical.value === "all" || option.dataset.vertical === vertical.value);
    [...task.options].forEach((option) => {{ option.hidden = !eligible.includes(option); }});
    if (!eligible.includes(task.selectedOptions[0])) task.value = eligible[0].value;
    render();
  }};
  vertical.addEventListener("change", syncTasks);
  [task, metric, ...toggles].forEach((control) => control.addEventListener("change", render));
  task.value = "H1";
  syncTasks();
}})();
</script>
"""


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Universal Agent Benchmark · Formal Controlled Pilot</title>
<style>
  :root {{ --bg:#E7EAF0; --surface:#FFFFFF; --surface-2:#F4F6F9; --ink:#14171C; --muted:#5A6472; --faint:#8B94A3; --line:#D9DEE6; --accent:#3B4CC0; --ok:#12875A; --fail:#CF3A54; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; background: var(--bg); color: var(--ink); font-size: 14px; }}
  .mono {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; }}
  .app {{ display: grid; grid-template-columns: 248px minmax(0, 1fr); min-height: 100vh; }}
  .rail {{ position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 20px 18px; background: var(--surface); border-right: 1px solid var(--line); }}
  .brand {{ font-weight: 750; font-size: 15px; }}
  .brand-version {{ margin-left: 6px; color: var(--faint); font: 11px ui-monospace, monospace; }}
  .rail-sub, .rail-note {{ color: var(--muted); font-size: 12px; }}
  .rail-sub {{ margin: 2px 0 22px; }}
  .rail-note {{ border-top: 1px solid var(--line); margin-top: 20px; padding-top: 14px; }}
  .control {{ margin-bottom: 20px; }}
  .control > label, .control-label {{ display: block; margin-bottom: 8px; color: var(--faint); font-size: 11px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
  select {{ width: 100%; padding: 8px 9px; border: 1px solid #C3CAD5; border-radius: 8px; background: var(--surface-2); color: var(--ink); font: 12px ui-monospace, monospace; }}
  select:focus-visible, input:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  .framework-toggles {{ display: grid; gap: 7px; }}
  .framework-toggle {{ display: flex; align-items: center; gap: 8px; padding: 7px 8px; border: 1px solid var(--line); border-radius: 8px; cursor: pointer; font: 12px ui-monospace, monospace; }}
  .framework-toggle span {{ width: 9px; height: 9px; border-radius: 2px; }}
  main {{ width: 100%; max-width: 1280px; padding: 24px 30px 60px; }}
  .head {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 18px; flex-wrap: wrap; margin-bottom: 18px; }}
  h1 {{ font-size: 21px; margin: 0 0 4px; }}
  .head p, .meta, .hint {{ color: var(--muted); font-size: 12px; }}
  .head p {{ margin: 0; }}
  .meta {{ text-align: right; font-family: ui-monospace, monospace; }}
  .banner {{ margin-bottom: 20px; padding: 11px 14px; border: 1px solid #EBD79A; border-radius: 9px; background: #FAF0D2; color: #735900; font: 700 11.5px ui-monospace, monospace; }}
  .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }}
  .summary-card, .card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 5px 18px rgba(20,23,28,.05); }}
  .summary-card {{ padding: 14px 16px; }}
  .summary-card strong {{ display: block; font: 700 22px ui-monospace, monospace; }}
  .summary-card span {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
  section {{ margin-bottom: 30px; }}
  .section-head {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }}
  h2 {{ margin: 0; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
  .section-head span {{ color: var(--faint); font-size: 12px; }}
  .hint {{ margin: 0 0 13px; }}
  .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; font-size: 12px; }}
  th {{ background: var(--surface-2); color: var(--muted); font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.totals td {{ font-weight: 700; background: var(--surface-2); }}
  td.cell.pending {{ color: var(--faint); font-family: ui-monospace, monospace; }}
  td.cell.complete {{ color: var(--ok); font-family: ui-monospace, monospace; }}
  td.cell.error {{ color: var(--fail); font-family: ui-monospace, monospace; }}
  .card {{ padding: 15px 16px; }}
  .card-title {{ color: var(--muted); font-size: 12px; margin-bottom: 10px; }}
  .comparison-card {{ margin-bottom: 14px; }}
  .comparison-row {{ display: grid; grid-template-columns: minmax(150px, 190px) minmax(180px, 1fr) minmax(145px, auto); align-items: center; gap: 12px; margin: 10px 0; font-size: 12px; }}
  .comparison-row.invalid {{ color: #7A271A; }}
  .comparison-row.invalid .bar-track {{ background: repeating-linear-gradient(135deg, #FEE4E2, #FEE4E2 6px, #FFF 6px, #FFF 12px); }}
  .comparison-row.unavailable {{ color: #5A6472; }}
  .empty {{ margin: 4px 0; color: #5A6472; font-size: 12px; }}
  .bar-row {{ display: grid; grid-template-columns: 150px 1fr 70px; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 12px; }}
  .bar-track {{ height: 10px; border-radius: 4px; background: var(--surface-2); border: 1px solid var(--line); overflow: hidden; }}
  .bar-fill {{ height: 100%; }}
  .task-name {{ color: var(--muted); font-size: 11px; }}
  .suitability-matrix th.framework-cell, .suitability-matrix td.framework-cell {{ text-align: center; }}
  .score {{ display: inline-block; min-width: 54px; padding: 4px 7px; border-radius: 7px; font: 700 12px ui-monospace, monospace; }}
  .score.score {{ color: var(--ok); background: #DBF0E7; }}
  .score.invalid {{ color: #7A271A; background: #FEE4E2; }}
  details {{ margin-top: 8px; }}
  summary {{ cursor: pointer; color: var(--muted); font-weight: 700; margin-bottom: 12px; }}
  [hidden] {{ display: none !important; }}
  @media (max-width: 860px) {{
    .app {{ grid-template-columns: 1fr; }}
    .rail {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
    main {{ padding: 20px 14px 40px; }}
    .summary {{ grid-template-columns: repeat(2, 1fr); }}
    .comparison-row {{ grid-template-columns: 1fr; gap: 5px; }}
  }}
</style>
</head>
<body>
  <div class="app">
    <aside class="rail">
      <div class="brand">Universal Agent<span class="brand-version">formal v2.0</span></div>
      <p class="rail-sub">Cross-vertical framework evaluation</p>
      {control_rail}
      <p class="rail-note">Healthcare and E-commerce share one frozen adapter/evaluator pipeline. Gold, prompts, traces, run IDs, hashes, and private environments remain local.</p>
    </aside>
    <main>
      <div class="head"><div><h1>Formal benchmark dashboard</h1><p>LangGraph · CrewAI · OpenAI Agents SDK across two verticals and eight tasks.</p></div>
        <div class="meta">Generated {generated_at}<br>Gate: {gate_status}</div></div>
      <div class="banner">{banner_text}</div>
      <div class="summary">{overview}</div>
      {results}
      <details><summary>Frozen execution matrix and representative-case counts</summary>
        <p class="hint">Counts are frozen per docs/representative_case_ids.md and docs/experiment_report_skeleton.md.</p>
        <div class="table-wrap"><table><thead><tr><th>Task</th><th>Cases</th><th>Preflights</th><th>Main runs</th>
          <th>Representative case</th><th>Repeats</th><th>Controlled total</th>{framework_headers}</tr></thead>
          <tbody>{task_rows}<tr class="totals"><td>Total</td><td>{total_cases}</td><td>{total_preflights}</td>
          <td>{total_main_runs}</td><td>8 IDs</td><td>{total_repeats}</td><td>{total_controlled}</td><td colspan="{framework_count}"></td></tr></tbody>
        </table></div>
      </details>
    </main>
  </div>
  {interaction_script}
</body>
</html>
"""


def render_html(payload: dict) -> str:
    banner_text = (
        'No result data is loaded; every status cell below is "pending" by construction, not a measured outcome.'
        if payload["aggregate"] is None
        else "A privacy-reviewed aggregate candidate is loaded; claims review is complete and public-release authorization remains a separate gate."
    )
    return HTML_TEMPLATE.format(
        generated_at=payload["generated_at"],
        gate_status=payload["gate_status"],
        banner_text=banner_text,
        control_rail=_control_rail_html(payload),
        overview=_overview_html(payload),
        framework_headers=_framework_headers_html(payload),
        task_rows=_task_rows_html(payload),
        total_cases=payload["totals"]["cases"],
        total_preflights=payload["totals"]["preflights"],
        total_main_runs=payload["totals"]["main_runs"],
        total_repeats=payload["totals"]["repeats"],
        total_controlled=payload["totals"]["controlled_total"],
        framework_count=len(payload["frameworks"]),
        results=_results_html(payload),
        interaction_script=_interaction_script(payload),
    )


def build(aggregate_path: Path | None = None, freeze_path: Path | None = None) -> str:
    aggregate = _load_json(aggregate_path) if aggregate_path else None
    freeze = _load_json(freeze_path) if freeze_path else None
    return render_html(build_payload(aggregate, freeze))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate", type=Path)
    parser.add_argument("--freeze-confirmation", type=Path)
    args = parser.parse_args()
    if bool(args.aggregate) != bool(args.freeze_confirmation):
        parser.error("--aggregate and --freeze-confirmation must be used together")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build(args.aggregate, args.freeze_confirmation), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
