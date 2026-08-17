#!/usr/bin/env python3
"""Placeholder (v0) WS4/WS5 controlled-pilot dashboard.

Renders results/pilot_dashboard.html: a structural preview of the frozen
60-case controlled-pilot run matrix (docs/representative_case_ids.md,
docs/experiment_report_skeleton.md). The controlled pilot has not executed
--  gate status is `technical_smoke_only` -- so every cell is intentionally
"pending". This script never fabricates run outcomes; it only lays out the
already-frozen task/case/repeat counts so the real dashboard has a known
shape to fill in once results exist.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_dashboard import FRAMEWORK_COLORS, FRAMEWORK_LABELS, KNOWN_FRAMEWORK_ORDER

OUTPUT_PATH = ROOT / "results" / "pilot_dashboard.html"

GATE_STATUS = "technical_smoke_only"

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


def build_payload() -> dict:
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
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "gate_status": GATE_STATUS,
        "frameworks": frameworks,
        "tasks": tasks,
        "totals": totals,
    }


def _task_rows_html(payload: dict) -> str:
    rows = []
    for task in payload["tasks"]:
        status_cells = "".join(
            f'<td class="cell pending">pending</td>' for _ in payload["frameworks"]
        )
        rows.append(
            f"<tr><td class=\"mono\">{task['task_id']}</td>"
            f"<td>{task['cases']}</td>"
            f"<td>{task['preflights']}</td>"
            f"<td>{task['main_runs']}</td>"
            f"<td class=\"mono\">{task['representative_case_id']}</td>"
            f"<td>{task['repeats']}</td>"
            f"<td>{task['controlled_total']}</td>"
            f"{status_cells}</tr>"
        )
    return "\n".join(rows)


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


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>WS4 Controlled Pilot Dashboard (placeholder)</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 24px 30px 60px; background: #E7EAF0; color: #14171C; }}
  .mono {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; }}
  .faint {{ color: #8B94A3; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: #5A6472; margin: 0 0 8px; }}
  .hint {{ color: #5A6472; font-size: 12.5px; margin: 0 0 14px; }}
  .banner {{ margin: 14px 0 22px; padding: 12px 14px; border: 1px solid #EBD79A; border-radius: 8px; background: #FAF0D2; color: #735900; font-weight: 600; font-size: 12.5px; }}
  section {{ margin-bottom: 28px; }}
  table {{ border-collapse: collapse; width: 100%; background: #FFFFFF; border: 1px solid #D9DEE6; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 8px 12px; border-bottom: 1px solid #D9DEE6; text-align: left; font-size: 12.5px; }}
  th {{ background: #F4F6F9; text-transform: uppercase; font-size: 10.5px; letter-spacing: .05em; color: #5A6472; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.totals td {{ font-weight: 700; background: #F4F6F9; }}
  td.cell.pending {{ color: #98A2B1; font-family: ui-monospace, monospace; }}
  .card {{ background: #FFFFFF; border: 1px solid #D9DEE6; border-radius: 8px; padding: 14px 16px; }}
  .card-title {{ font-size: 12px; color: #5A6472; margin-bottom: 10px; }}
  .bar-row {{ display: grid; grid-template-columns: 150px 1fr 70px; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 12px; }}
  .bar-track {{ height: 10px; border-radius: 4px; background: #F4F6F9; border: 1px solid #D9DEE6; overflow: hidden; }}
  .bar-fill {{ height: 100%; }}
</style>
</head>
<body>
  <h1>WS4 controlled-pilot dashboard &mdash; placeholder v0</h1>
  <p class="hint">Generated {generated_at}. Structural preview only &mdash; not benchmark results.</p>
  <div class="banner">Gate status: {gate_status}. No controlled-pilot run has executed. Every status cell below is "pending" by construction, not a measured outcome.</div>

  <section>
    <h2>Frozen run matrix</h2>
    <p class="hint">Counts are frozen per docs/representative_case_ids.md and docs/experiment_report_skeleton.md.</p>
    <table>
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
    </table>
  </section>

  {figures}
</body>
</html>
"""


def render_html(payload: dict) -> str:
    return HTML_TEMPLATE.format(
        generated_at=payload["generated_at"],
        gate_status=payload["gate_status"],
        framework_headers=_framework_headers_html(payload),
        task_rows=_task_rows_html(payload),
        total_cases=payload["totals"]["cases"],
        total_preflights=payload["totals"]["preflights"],
        total_main_runs=payload["totals"]["main_runs"],
        total_repeats=payload["totals"]["repeats"],
        total_controlled=payload["totals"]["controlled_total"],
        framework_count=len(payload["frameworks"]),
        figures=_figure_placeholders_html(payload),
    )


def build() -> str:
    return render_html(build_payload())


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
