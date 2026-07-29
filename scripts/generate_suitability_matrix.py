#!/usr/bin/env python3
"""Generate the Framework Suitability Matrix -- the final deliverable per
CLAUDE.md, comparing LangGraph, CrewAI, and OpenAI Agents SDK across the
Medical Diagnostic and E-commerce Trend Researcher verticals.

Pulls from the latest result per (task_id, framework, model) in
results/metrics/*.jsonl and writes a single Markdown report with summary
tables and ASCII bar charts to results/framework_suitability_matrix.md.
"""

import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.evaluator import evaluate_hallucination_risk, evaluate_medical_safety, evaluate_result
from adapter.ground_truth import GROUND_TRUTH_CONFIG, load_ground_truth
from adapter.result_writer import load_latest_results, result_models
from adapter.schemas import AgentRunResult

FRAMEWORKS = ["openai_agents_sdk", "langgraph", "crewai"]

OUTPUT_PATH = ROOT / "results" / "framework_suitability_matrix.md"


def _read_env_var(key: str, default: str) -> str:
    """Minimal stdlib-only .env reader -- just enough to label the report
    with the current model, without adding a python-dotenv dependency to a
    script that otherwise only needs the standard library."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return default
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == key:
            return value.strip()
    return default


def _bar(pct: float, width: int = 20) -> str:
    filled = round(max(0, min(100, pct)) / 100 * width)
    return "#" * filled + "-" * (width - filled)


def _vertical_stats(vertical: str, model_name: str) -> dict[str, dict | None]:
    config = GROUND_TRUTH_CONFIG.get(vertical)
    ground_truth = load_ground_truth(vertical) if config else {}
    results = load_latest_results(vertical, model_name=model_name)

    by_framework: dict[str, list[dict]] = defaultdict(list)
    for (_task_id, framework, _experiment_label), r in results.items():
        by_framework[framework].append(r)

    stats: dict[str, dict | None] = {}
    for framework in FRAMEWORKS:
        rows = by_framework.get(framework, [])
        n = len(rows)
        if n == 0:
            stats[framework] = None
            continue

        results_objs = [AgentRunResult(**r) for r in rows]
        metrics_list = [evaluate_result(r) for r in results_objs]
        avg_latency = sum(r.latency_seconds for r in results_objs) / n
        failure_modes = Counter(m["failure_mode"] for m in metrics_list)
        tool_overuse_count = sum(1 for m in metrics_list if m["tool_overuse"])

        accuracy = None
        confidently_wrong = None
        if config:
            hallu = [
                evaluate_hallucination_risk(r, ground_truth[r.task_id], config["answer_key"])
                for r in results_objs
                if r.task_id in ground_truth
            ]
            if hallu:
                correct = sum(1 for h in hallu if h["answer_correct"])
                accuracy = correct / len(hallu)
                confidently_wrong = sum(1 for h in hallu if h["confidently_wrong"])

        medical_safety_ok = None
        if vertical == "medical_diagnostic":
            safety = [evaluate_medical_safety(r) for r in results_objs]
            medical_safety_ok = sum(1 for s in safety if s["medical_safety_ok"])

        stats[framework] = {
            "n": n,
            "avg_latency": avg_latency,
            "failure_modes": failure_modes,
            "tool_overuse_count": tool_overuse_count,
            "accuracy": accuracy,
            "confidently_wrong": confidently_wrong,
            "medical_safety_ok": medical_safety_ok,
        }
    return stats


def _render_vertical_section(title: str, vertical: str, stats: dict) -> list[str]:
    lines = [f"## {title}", ""]
    has_accuracy = GROUND_TRUTH_CONFIG.get(vertical) is not None
    has_medical_safety = vertical == "medical_diagnostic"

    header = ["Framework", "n"]
    if has_accuracy:
        header += ["Accuracy", "Confidently Wrong"]
    if has_medical_safety:
        header.append("Medical Safety OK")
    header += ["Tool Overuse", "Avg Latency", "Failure Modes"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))

    for framework in FRAMEWORKS:
        s = stats.get(framework)
        if s is None:
            row = [framework, "0"]
            row += ["n/a", "n/a"] if has_accuracy else []
            row += ["n/a"] if has_medical_safety else []
            row += ["n/a", "n/a", "no data"]
            lines.append("| " + " | ".join(row) + " |")
            continue

        row = [framework, str(s["n"])]
        if has_accuracy:
            acc = (
                f"{s['accuracy'] * 100:.0f}% ({round(s['accuracy'] * s['n'])}/{s['n']})"
                if s["accuracy"] is not None
                else "n/a"
            )
            cw = f"{s['confidently_wrong']}/{s['n']}" if s["confidently_wrong"] is not None else "n/a"
            row += [acc, cw]
        if has_medical_safety:
            row.append(f"{s['medical_safety_ok']}/{s['n']}" if s["medical_safety_ok"] is not None else "n/a")
        row.append(f"{s['tool_overuse_count']}/{s['n']}")
        row.append(f"{s['avg_latency']:.1f}s")
        row.append(", ".join(f"{k}={v}" for k, v in s["failure_modes"].most_common()))
        lines.append("| " + " | ".join(row) + " |")

    if has_accuracy and any(s and s["accuracy"] is not None for s in stats.values()):
        lines += ["", "**Accuracy:**", "```"]
        for framework in FRAMEWORKS:
            s = stats.get(framework)
            if s is None or s["accuracy"] is None:
                continue
            pct = s["accuracy"] * 100
            lines.append(f"{framework:<20} {_bar(pct)} {pct:5.1f}%")
        lines.append("```")

    latencies = [s["avg_latency"] for s in stats.values() if s]
    if latencies:
        lines += ["", "**Avg latency (s):**", "```"]
        max_latency = max(latencies) or 1
        for framework in FRAMEWORKS:
            s = stats.get(framework)
            if s is None:
                continue
            pct = s["avg_latency"] / max_latency * 100
            lines.append(f"{framework:<20} {_bar(pct)} {s['avg_latency']:5.1f}s")
        lines.append("```")
    lines.append("")
    return lines


QUALITATIVE_FINDINGS = """\
## Qualitative Findings (this session)

These come from targeted tests run during development, not just the raw metrics above:

- **Tool-failure resilience differs by framework.** When the mock tool raises an \
exception, `openai_agents_sdk` and `crewai` catch it internally and let the model \
recover with a graceful best-effort answer. `langgraph`'s default `ToolNode` only \
catches malformed tool-call errors, not arbitrary exceptions raised inside tool \
execution -- the task fails outright instead of degrading gracefully, unless \
`handle_tool_errors` is explicitly configured.
- **Tool overuse is model-dependent, not a fixed framework trait.** Under \
`gpt-4o-mini`, `crewai` calls the (unneeded) literature-lookup tool on the large \
majority of medical tasks despite being told not to -- 11/15 and, in a later re-run, \
9/10, so it's consistent under this model, not a one-off. The same tool-overuse \
tendency vanished entirely under both `gpt-5-nano` and `gpt-5.4-mini` (0/15, 0/15).
- **Schema drift found and fixed.** `crewai` was intermittently nesting the entire \
answer under an `"answer"` wrapper key on e-commerce tasks instead of the flat schema \
the prompt asked for. Root cause: `frameworks/crewai_agent/run.py`'s `Task.expected_output` \
was hardcoded to the smoke-test schema (`task_id, answer, safety_note`) for every \
vertical, directly contradicting the richer schema specified in the medical/e-commerce \
prompts -- CrewAI was being given two conflicting format instructions. Fixed by making \
`expected_output` generic ("matches the schema specified in the task description \
above"); a fresh full re-run afterward came back 10/10 clean, flat-schema output.
- **Escalation instruction is dropped by all three frameworks.** When the model \
answers "maybe" on a medical task, the prompt explicitly asks it to recommend a \
qualified medical professional review the primary literature. All three frameworks \
correctly reason about uncertainty ("not statistically significant") but skip \
this specific referral language.
- **`gpt-4o-mini` has a near-universal `"safety_note"` -> `"safe_note"` typo on \
medical tasks.** In the latest full sweep, `langgraph` and `crewai` misspelled the key \
on 10/10 medical tasks, `openai_agents_sdk` on 8/10 -- despite the prompt spelling out \
`safety_note` exactly. The model's actual reasoning and uncertainty handling is fine; \
this is a narrow but near-total literal-key-compliance failure specific to this model, \
and it silently defeats the exact-disclaimer safety check unless something normalizes \
or fuzzy-matches the key.
- **Model choice affects latency far more than accuracy.** `gpt-4o-mini` averaged \
~3-5s/call; `gpt-5-nano` and `gpt-5.4-mini` averaged 8-24s/call (occasional 100s+ \
outliers) for similar or modestly better accuracy on the harder e-commerce trend task.

## Recommendation

- **Medical Diagnostic Assistant** (low tolerance for hallucination, structured \
reasoning, safe refusal): reasoning quality (accuracy, uncertainty handling) is solid \
across all three frameworks, but literal safety-disclaimer compliance is currently \
poor under `gpt-4o-mini` specifically (see the `safe_note` typo finding above) -- this \
vertical should not be called safety-compliant as configured today, independent of \
framework choice. `openai_agents_sdk` and `crewai` are the safer picks on tool \
discipline under a failing tool (graceful degradation); `crewai`'s tool-overuse under \
`gpt-4o-mini` is a second, separate risk to weigh if that model stays in use. All three \
need explicit prompting/validation work on both the escalation-language and exact-key \
requirements before this vertical could be called safety-compliant.
- **E-commerce Trend Researcher** (creative reasoning, frequent tool use, flexible \
synthesis): accuracy is the binding constraint here (40-80% depending on model), not \
framework choice -- all three show the same trend-direction reasoning weaknesses \
(a recency bias toward "declining" regardless of the actual multi-year pattern). \
Schema compliance is no longer a differentiator now that the `crewai` expected_output \
conflict is fixed -- all three produced clean flat JSON in the latest sweep.
"""


def main():
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    verticals = ["smoke_test", "medical_diagnostic", "ecommerce_trend_research"]
    models = sorted({model for vertical in verticals for model in result_models(vertical)})

    lines = [
        "# Framework Suitability Matrix",
        "",
        f"Generated: {generated_at}",
        "",
        "**Grouping rule:** results are separated by the model recorded at execution time. "
        "Legacy rows created before model metadata was added appear only under `unknown` and "
        "must not be used for model-controlled framework comparisons.",
        "",
    ]

    if not models:
        lines += ["No recorded runs were found.", ""]
    for model_name in models:
        lines += [f"# Model: `{model_name}`", ""]
        lines += _render_vertical_section(
            "Smoke Test", "smoke_test", _vertical_stats("smoke_test", model_name)
        )
        lines += _render_vertical_section(
            "Medical Diagnostic Assistant",
            "medical_diagnostic",
            _vertical_stats("medical_diagnostic", model_name),
        )
        lines += _render_vertical_section(
            "E-commerce Trend Researcher",
            "ecommerce_trend_research",
            _vertical_stats("ecommerce_trend_research", model_name),
        )

    lines.append(QUALITATIVE_FINDINGS)

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote in at {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
