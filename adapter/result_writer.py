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


def load_latest_results(vertical: str) -> dict[tuple[str, str], dict]:
    """Read results/metrics/<vertical>_results.jsonl and keep only the
    latest row per (task_id, framework) -- results are append-only, so
    older duplicate runs are superseded by newer ones for the same key."""
    path = default_result_path(vertical)
    latest: dict[tuple[str, str], dict] = {}
    if not path.exists():
        return latest
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            latest[(d["task_id"], d["framework"])] = d
    return latest
