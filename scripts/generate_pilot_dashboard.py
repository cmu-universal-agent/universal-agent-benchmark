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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_dashboard import FRAMEWORK_COLORS, FRAMEWORK_LABELS, KNOWN_FRAMEWORK_ORDER

OUTPUT_PATH = ROOT / "results" / "pilot_dashboard.html"
REPORT_PATH = ROOT / "docs" / "experiment_report_skeleton.md"

# Frozen per docs/representative_case_ids.md and docs/experiment_report_skeleton.md.
WS4_TASKS = [
    {"task_id": "H1", "cases": 8, "representative_case_id": "H1-REVIEW-001"},
    {"task_id": "H2", "cases": 8, "representative_case_id": "H2-REVIEW-001"},
    {"task_id": "H4", "cases": 8, "representative_case_id": "H4-REVIEW-001"},
    {"task_id": "H5", "cases": 8, "representative_case_id": "H5-REVIEW-001"},
    {"task_id": "E1", "cases": 8, "representative_case_id": "E1-REVIEW-001"},
    {"task_id": "E2", "cases": 8, "representative_case_id": "E2-REVIEW-001"},
    {"task_id": "E3", "cases": 8, "representative_case_id": "E3-REVIEW-001"},
    {"task_id": "E5", "cases": 4, "representative_case_id": "E5-001"},
]
FRAMEWORKS_PER_TASK = 3
REPEATS_PER_REPRESENTATIVE_CASE = 2  # additional targeted repeats, one representative case per task

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
    if freeze.get("experiment_id") != aggregate.get("experiment_id"):
        raise ValueError("aggregate and freeze experiment IDs differ")
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
    if sum(row["n"] for row in aggregate["rows"]) != 228:
        raise ValueError("aggregate must contain 24 task/framework rows and 228 results")
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
            f'<tr><td class="mono">{row["task_id"]}</td>'
            f'<td>{FRAMEWORK_LABELS[row["framework"]]}</td><td>{row["n"]}</td>'
            f'<td>{row["process_success"]}</td><td>{row["schema_valid"]}</td>'
            f'<td>{result}</td><td>{_metric(row["avg_latency_seconds"], 2)}</td>'
            f'<td>{_metric(row["estimated_cost_usd"], 6)}</td></tr>'
        )
    stable = sum(row["stable"] for row in aggregate["targeted_repeats"])
    release = "authorized" if aggregate["public_release_authorized"] else "not authorized"
    return f"""
    <section>
      <h2>Privacy-reviewed aggregate candidate</h2>
      <p class="hint">Claims approved; public release is {release}. {escape(aggregate['claim_boundary'])}</p>
      <div class="table-wrap"><table><thead><tr><th>Task</th><th>Framework</th><th>N</th><th>Process success</th>
        <th>Schema valid</th><th>Task-specific result</th><th>Avg latency (s)</th><th>Est. cost (USD)</th>
      </tr></thead><tbody>{''.join(rows)}</tbody></table></div>
      <p class="hint">Targeted-repeat stability: {stable}/24 complete rows stable. Invalid E5 sweep(s): {escape(', '.join(aggregate['invalid_e5_frameworks']) or 'none')}.</p>
    </section>
    """


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>WS4 Controlled Pilot Dashboard</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 24px 30px 60px; background: #E7EAF0; color: #14171C; }}
  .mono {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; }}
  .faint {{ color: #8B94A3; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: #5A6472; margin: 0 0 8px; }}
  .hint {{ color: #5A6472; font-size: 12.5px; margin: 0 0 14px; }}
  .banner {{ margin: 14px 0 22px; padding: 12px 14px; border: 1px solid #EBD79A; border-radius: 8px; background: #FAF0D2; color: #735900; font-weight: 600; font-size: 12.5px; }}
  section {{ margin-bottom: 28px; }}
  .table-wrap {{ overflow-x: auto; border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; background: #FFFFFF; border: 1px solid #D9DEE6; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 8px 12px; border-bottom: 1px solid #D9DEE6; text-align: left; font-size: 12.5px; }}
  th {{ background: #F4F6F9; text-transform: uppercase; font-size: 10.5px; letter-spacing: .05em; color: #5A6472; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.totals td {{ font-weight: 700; background: #F4F6F9; }}
  td.cell.pending {{ color: #98A2B1; font-family: ui-monospace, monospace; }}
  td.cell.complete {{ color: #276749; font-family: ui-monospace, monospace; }}
  td.cell.error {{ color: #B42318; font-family: ui-monospace, monospace; }}
  .card {{ background: #FFFFFF; border: 1px solid #D9DEE6; border-radius: 8px; padding: 14px 16px; }}
  .card-title {{ font-size: 12px; color: #5A6472; margin-bottom: 10px; }}
  .bar-row {{ display: grid; grid-template-columns: 150px 1fr 70px; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 12px; }}
  .bar-track {{ height: 10px; border-radius: 4px; background: #F4F6F9; border: 1px solid #D9DEE6; overflow: hidden; }}
  .bar-fill {{ height: 100%; }}
</style>
</head>
<body>
  <h1>WS4 controlled-pilot dashboard</h1>
  <p class="hint">Generated {generated_at}.</p>
  <div class="banner">Gate status: {gate_status}. {banner_text}</div>

  <section>
    <h2>Frozen run matrix</h2>
    <p class="hint">Counts are frozen per docs/representative_case_ids.md and docs/experiment_report_skeleton.md.</p>
    <div class="table-wrap"><table>
      <thead><tr>
        <th>Task</th><th>Cases</th><th>Preflights</th><th>Main runs</th>
        <th>Representative case</th><th>Repeats</th><th>Controlled total</th>
        {framework_headers}
      </tr></thead>
      <tbody>
        {task_rows}
        <tr class="totals"><td>Total</td><td>{total_cases}</td><td>{total_preflights}</td>
          <td>{total_main_runs}</td><td>8 IDs</td><td>{total_repeats}</td><td>{total_controlled}</td>
          <td colspan="{framework_count}"></td></tr>
      </tbody>
    </table></div>
  </section>

  {results}
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
        framework_headers=_framework_headers_html(payload),
        task_rows=_task_rows_html(payload),
        total_cases=payload["totals"]["cases"],
        total_preflights=payload["totals"]["preflights"],
        total_main_runs=payload["totals"]["main_runs"],
        total_repeats=payload["totals"]["repeats"],
        total_controlled=payload["totals"]["controlled_total"],
        framework_count=len(payload["frameworks"]),
        results=_results_html(payload),
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
