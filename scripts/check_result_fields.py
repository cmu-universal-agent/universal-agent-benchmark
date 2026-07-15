#!/usr/bin/env python3
"""Generate a framework field-availability matrix from recorded JSONL runs.

This is a read-only audit. It does not call a model and is safe to run while
the shared schemas are still under review.
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results" / "metrics"
OUTPUT_PATH = ROOT / "results" / "framework_field_availability.md"

FIELDS = [
    "run_id",
    "experiment_id",
    "framework_version",
    "model_provider",
    "model_name",
    "temperature",
    "prompt_version",
    "started_at",
    "completed_at",
    "raw_output",
    "tool_calls",
    "token_usage",
]


def _recorded(row: dict, field: str) -> bool:
    if field not in row:
        return False
    value = row[field]
    if field in {"tool_calls"}:
        return isinstance(value, list)
    if field == "token_usage":
        return isinstance(value, dict) and {
            "input_tokens",
            "output_tokens",
            "total_tokens",
        }.issubset(value)
    return value not in (None, "")


def main() -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in sorted(RESULTS_DIR.glob("*_results.jsonl")):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                framework = row.get("framework", "unknown")
                model = row.get("model_name") or "unknown"
                groups[(framework, model)].append(row)

    lines = [
        "# Framework Field Availability",
        "",
        "Generated from the recorded JSONL rows. `unknown` model rows are legacy development results and must not be used for model-controlled comparisons.",
        "",
    ]

    if not groups:
        lines += ["No result rows were found.", ""]
    else:
        header = ["Framework", "Model", "Rows", *FIELDS]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))
        for (framework, model), rows in sorted(groups.items()):
            cells = [framework, model, str(len(rows))]
            for field in FIELDS:
                count = sum(_recorded(row, field) for row in rows)
                cells.append(f"{count}/{len(rows)}")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    lines += [
        "## Interpretation",
        "",
        "- `n/n`: field is recorded for every row in the group.",
        "- `0/n`: field is missing or null for every row.",
        "- A partial count means the adapter or result format changed between runs.",
        "- Empty `tool_calls` is valid for a no-tool run.",
        "- A present `token_usage` object may still contain null counts when the provider does not expose usage through the framework adapter.",
        "",
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
