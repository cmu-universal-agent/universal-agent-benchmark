import json
from dataclasses import asdict
from pathlib import Path

from adapter.schemas import AgentRunResult

RESULTS_ROOT = Path(__file__).resolve().parents[1] / "results" / "metrics"


def default_result_path(vertical: str) -> Path:
    return RESULTS_ROOT / f"{vertical}_results.jsonl"


def append_result(result: AgentRunResult, path: Path | None = None) -> Path:
    """Append a single AgentRunResult as one JSON line to a results file."""
    target = path or default_result_path(result.vertical)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(result)) + "\n")
    return target
