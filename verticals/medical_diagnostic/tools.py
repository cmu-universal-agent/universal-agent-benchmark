"""Mock tool for the medical_diagnostic vertical.

Reads only from the already-downloaded local PubMedQA cache
(data/pubmedqa/ori_pqal.json) -- there is no live network call or real
external API involved. Framework-agnostic on purpose: each framework's
run.py wraps `search_literature` in its own tool-calling API, but they all
call this same function, so `call_log` below is a single source of truth
for tool_call_count regardless of which framework's tool-calling plumbing
was used.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "data" / "pubmedqa" / "ori_pqal.json"

_dataset: dict | None = None

call_log: list[str] = []

_simulate_failure = False


def _load_dataset() -> dict:
    global _dataset
    if _dataset is None:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            _dataset = json.load(f)
    return _dataset


def reset_call_log() -> None:
    call_log.clear()


def set_simulate_failure(enabled: bool) -> None:
    """Testing hook: make the next search_literature call(s) raise, to see
    how each framework/run_task handles a failing tool."""
    global _simulate_failure
    _simulate_failure = enabled


def search_literature(pubmed_id: str) -> str:
    """Look up the research abstract for a given PubMed ID."""
    call_log.append(pubmed_id)
    if _simulate_failure:
        raise RuntimeError("Simulated tool failure: literature search unavailable")
    dataset = _load_dataset()
    entry = dataset.get(pubmed_id)
    if entry is None:
        return f"No abstract found for PubMed ID {pubmed_id}."
    return " ".join(entry["CONTEXTS"])
