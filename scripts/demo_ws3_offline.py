#!/usr/bin/env python3
"""Run a deterministic contract-only WS3 demo with synthetic evidence."""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import validate_ws3_tau_retail_contract as validator  # noqa: E402


def run_demo(evidence_out: Path | None = None) -> dict[str, Any]:
    contract = validator._load(validator.CONTRACT_PATH)
    fixture = validator._load(validator.FIXTURE_PATH)
    operations = validator._validate_registry(contract, fixture)
    scenarios, calls = validator._validate_scenarios(
        contract, fixture, operations
    )
    validator._validate_leakage(fixture)

    internal_evidence = {
        "contract_version": contract["contract_version"],
        "framework": "langgraph",
        "wrapper_version": "synthetic-contract-fixture",
        "generated_at": "2026-07-22T00:00:00Z",
        "reset_determinism": fixture["reset_determinism"],
        "scenarios": fixture["scenarios"],
    }
    validator._validate_wrapper_envelope(internal_evidence)

    by_id = {row["fixture_id"]: row for row in fixture["scenarios"]}
    read = by_id["read_success"]
    write = by_id["write_success"]
    invalid = by_id["invalid_arguments"]
    disallowed = by_id["disallowed_tool"]
    failure = by_id["tool_failure"]
    duplicate = by_id["duplicate_action"]
    summary = {
        "version": contract["contract_version"],
        "tools": len(operations),
        "scenarios": scenarios,
        "calls": calls,
        "reset_deterministic": (
            fixture["reset_determinism"]["first"]["state_sha256"]
            == fixture["reset_determinism"]["second"]["state_sha256"]
        ),
        "read_tool": read["events"][0]["call"]["tool_name"],
        "read_state_changed": (
            read["events"][0]["state_before_sha256"]
            != read["events"][0]["state_after_sha256"]
        ),
        "write_tool": write["events"][0]["call"]["tool_name"],
        "write_mutation_count": write["final_state"]["mutation_count"],
        "invalid_error": invalid["events"][0]["call"]["error"]["error_type"],
        "disallowed_error": disallowed["events"][0]["call"]["error"]["error_type"],
        "failure_error": failure["events"][0]["call"]["error"]["error_type"],
        "failure_recovered": failure["events"][-1]["call"]["outcome"] == "success",
        "duplicate_tool": duplicate["events"][-1]["call"]["tool_name"],
        "duplicate_error": duplicate["events"][-1]["call"]["error"]["error_type"],
        "duplicate_state_changed": (
            duplicate["events"][-1]["state_before_sha256"]
            != duplicate["events"][-1]["state_after_sha256"]
        ),
        "leakage": 0,
    }

    if evidence_out is not None:
        public_evidence = {
            "artifact_type": "synthetic_technical_validation",
            "contract_version": summary["version"],
            "validation": {
                "tool_registry_valid": True,
                "state_schema_valid": True,
                "trace_schema_valid": True,
                "reset_deterministic": summary["reset_deterministic"],
                "privacy_scan_passed": summary["leakage"] == 0,
            },
            "coverage": {
                "canonical_tools": summary["tools"],
                "scenarios": summary["scenarios"],
                "tool_calls": summary["calls"],
                "read": "pass",
                "mutation": "pass",
                "invalid_arguments": "pass",
                "disallowed_tool": "pass",
                "duplicate_action": "pass",
                "tool_failure_recovery": "pass",
                "leakage_guard": "pass",
            },
            "artifact_scope": {
                "included_real_wrapper": "langgraph",
                "wrappers_not_included": ["crewai", "openai_agents_sdk"],
            },
        }
        evidence_out.parent.mkdir(parents=True, exist_ok=True)
        evidence_out.write_text(
            json.dumps(public_evidence, indent=2) + "\n", encoding="utf-8"
        )
    return summary


def write_html(summary: dict[str, Any], output: Path) -> None:
    value = {key: escape(str(item)) for key, item in summary.items()}
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WS3 Retail Contract Demo</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #08111f; color: #e8eef7; }}
main {{ width: min(1080px, calc(100% - 32px)); margin: 48px auto; }}
header {{ padding: 34px; border: 1px solid #273852; border-radius: 20px;
  background: linear-gradient(135deg, #14233b, #0c1728); }}
h1 {{ margin: 12px 0 8px; font-size: clamp(2rem, 5vw, 3.5rem); letter-spacing: -.04em; }}
h2 {{ margin-top: 38px; }}
p {{ color: #9fb0c8; max-width: 760px; line-height: 1.6; }}
.badge {{ display: inline-block; padding: 7px 11px; border: 1px solid #f0b429;
  border-radius: 999px; color: #ffd166; font: 700 12px ui-monospace, monospace; }}
.grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 18px 0; }}
.card {{ padding: 20px; border: 1px solid #273852; border-radius: 14px; background: #101d30; }}
.metric {{ font-size: 2rem; font-weight: 750; }}
.label {{ color: #90a2bb; font-size: 13px; }}
table {{ width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 14px;
  border: 1px solid #273852; background: #101d30; }}
th, td {{ padding: 16px; text-align: left; border-bottom: 1px solid #273852; }}
th {{ color: #90a2bb; font-size: 12px; letter-spacing: .08em; }}
code {{ color: #8bd5ff; }}
.ok {{ color: #62d6a7; font-weight: 700; }}
.pending {{ color: #f6c85f; }}
footer {{ margin: 30px 0; color: #71839d; font-size: 13px; }}
@media (max-width: 760px) {{
  main {{ margin-top: 20px; }}
  .grid {{ grid-template-columns: repeat(2, 1fr); }}
  th:nth-child(3), td:nth-child(3) {{ display: none; }}
}}
</style>
</head>
<body>
<main>
<header>
  <span class="badge">TECHNICAL VALIDATION | SYNTHETIC ONLY | NOT BENCHMARK SCORES</span>
  <h1>WS3 Retail Contract Demo</h1>
  <p>A deterministic, leakage-safe meeting fallback proving the
  tool/state/reset/error contract without live model calls.</p>
</header>
<section class="grid" aria-label="Contract summary">
  <div class="card"><div class="metric">{value["version"]}</div><div class="label">contract version</div></div>
  <div class="card"><div class="metric">{value["tools"]}</div><div class="label">canonical tools</div></div>
  <div class="card"><div class="metric">{value["scenarios"]}</div><div class="label">validated scenarios</div></div>
  <div class="card"><div class="metric">{value["leakage"]}</div><div class="label">leakage findings</div></div>
</section>
<h2>Deterministic state transitions</h2>
<table>
<thead><tr><th>Gate</th><th>Canonical tool</th><th>Observed</th><th>Result</th></tr></thead>
<tbody>
<tr><td>Reset</td><td><code>reset(seed)</code></td>
  <td>repeat reset produced identical state</td><td class="ok">PASS</td></tr>
<tr><td>Read</td><td><code>{value["read_tool"]}</code></td>
  <td>state_changed={int(summary["read_state_changed"])}</td><td class="ok">PASS</td></tr>
<tr><td>Mutation</td><td><code>{value["write_tool"]}</code></td>
  <td>mutation_count={value["write_mutation_count"]}</td><td class="ok">PASS</td></tr>
<tr><td>Invalid input</td><td><code>structured error</code></td>
  <td>{value["invalid_error"]}</td><td class="ok">PASS</td></tr>
<tr><td>Disallowed action</td><td><code>allowed-tools gate</code></td>
  <td>{value["disallowed_error"]}</td><td class="ok">PASS</td></tr>
<tr><td>Duplicate</td><td><code>{value["duplicate_tool"]}</code></td>
  <td>{value["duplicate_error"]}; state_changed={int(summary["duplicate_state_changed"])}</td>
  <td class="ok">PASS</td></tr>
<tr><td>Injected failure</td><td><code>retry link</code></td>
  <td>{value["failure_error"]}; recovered={int(summary["failure_recovered"])}</td>
  <td class="ok">PASS</td></tr>
<tr><td>Leakage guard</td><td><code>visibility boundary</code></td>
  <td>findings={value["leakage"]}</td><td class="ok">PASS</td></tr>
</tbody>
</table>
<h2>Remaining integration gates</h2>
<div class="card pending">Included scope: shared core + one real LangGraph
wrapper. Three-framework parity still requires CrewAI and OpenAI wrappers.</div>
<footer>Synthetic technical validation only. No live model calls, scores,
or framework ranking.</footer>
</main>
</body>
</html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-out",
        type=Path,
        help="Optional path for presentation-safe synthetic evidence JSON.",
    )
    parser.add_argument(
        "--html-out",
        type=Path,
        default=ROOT / "results" / "ws3_demo.html",
        help="Meeting-ready static HTML output.",
    )
    args = parser.parse_args()
    summary = run_demo(args.evidence_out)
    write_html(summary, args.html_out)
    print("WS3_OFFLINE_DEMO technical_validation_only=1 benchmark_scores=0")
    print(
        f"CONTRACT_OK version={summary['version']} tools={summary['tools']}"
    )
    print(f"RESET_OK deterministic={int(summary['reset_deterministic'])}")
    print(
        f"READ_OK tool={summary['read_tool']} "
        f"state_changed={int(summary['read_state_changed'])}"
    )
    print(
        f"WRITE_OK tool={summary['write_tool']} "
        f"mutation_count={summary['write_mutation_count']}"
    )
    print(
        f"DUPLICATE_OK tool={summary['duplicate_tool']} "
        f"error={summary['duplicate_error']} "
        f"state_changed={int(summary['duplicate_state_changed'])}"
    )
    print(
        f"EVIDENCE_OK scenarios={summary['scenarios']} "
        f"calls={summary['calls']} leakage={summary['leakage']}"
    )
    if args.evidence_out is not None:
        print(f"EVIDENCE_FILE path={args.evidence_out}")
    print(f"DEMO_FILE path={args.html_out}")


if __name__ == "__main__":
    main()
