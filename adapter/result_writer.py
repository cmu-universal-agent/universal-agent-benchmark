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


def result_models(vertical: str) -> list[str]:
    """Return the model names present in a vertical's result file.

    Legacy rows created before model metadata was added are labeled unknown
    rather than being silently attributed to the model currently in .env.
    """
    path = default_result_path(vertical)
    if not path.exists():
        return []
    models: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            models.add(d.get("model_name") or "unknown")
    return sorted(models)


def load_latest_results(
    vertical: str,
    model_name: str | None = None,
) -> dict[tuple[str, str, str, str], dict]:
    """Read results/metrics/<vertical>_results.jsonl and keep only the
    latest attempt per logical run without folding cases or repeats.

    When model_name is provided, rows from other models are excluded. Legacy
    rows without model metadata belong to the explicit "unknown" group.
    """
    path = default_result_path(vertical)
    latest: dict[tuple[str, str, str, str], dict] = {}
    if not path.exists():
        return latest
    with open(path, "r", encoding="utf-8") as f:
        for row_number, line in enumerate(f, start=1):
            d = json.loads(line)
            row_model = d.get("model_name") or "unknown"
            if model_name is not None and row_model != model_name:
                continue
            case_id = d.get("case_id") or d["task_id"]
            experiment_id = d.get("experiment_id") or "legacy"
            logical_run_id = (
                d.get("logical_run_id")
                or d.get("run_id")
                or f"legacy-row-{row_number}"
            )
            key = (case_id, d["framework"], experiment_id, logical_run_id)
            previous = latest.get(key)
            if previous is None or (d.get("attempt") or 1) >= (
                previous.get("attempt") or 1
            ):
                latest[key] = d
    return latest
