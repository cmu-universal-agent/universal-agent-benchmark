"""Mock tool for the ecommerce_trend_research vertical.

Reads only from the already-downloaded local Amazon Reviews 2023 cache
(data/amazon_reviews_2023/) -- there is no live network call or real
external API involved. Framework-agnostic on purpose: each framework's
run.py wraps `get_review_history` in its own tool-calling API, but they all
call this same function, so `call_log` below is a single source of truth
for tool_call_count regardless of which framework's tool-calling plumbing
was used.
"""

import gzip
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "amazon_reviews_2023"
REVIEWS_CACHE = CACHE_DIR / "Subscription_Boxes.jsonl.gz"

_yearly_by_asin: dict[str, dict[int, list[float]]] | None = None

call_log: list[dict] = []

_simulate_failure = False


def set_simulate_failure(enabled: bool) -> None:
    """Testing hook: make the next get_review_history call(s) raise, to see
    how each framework/run_task handles a failing tool."""
    global _simulate_failure
    _simulate_failure = enabled


def _load_yearly_by_asin() -> dict[str, dict[int, list[float]]]:
    global _yearly_by_asin
    if _yearly_by_asin is None:
        by_product: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        with gzip.open(REVIEWS_CACHE, "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                year = datetime.fromtimestamp(r["timestamp"] / 1000, tz=timezone.utc).year
                by_product[r["parent_asin"]][year].append(r["rating"])
        _yearly_by_asin = by_product
    return _yearly_by_asin


def reset_call_log() -> None:
    call_log.clear()


def get_review_history(parent_asin: str) -> str:
    """Look up the yearly review-count and average-rating history for a product."""
    started_perf = time.perf_counter()
    record = {
        "schema_version": "1.0",
        "tool_call_id": f"tool-{uuid.uuid4().hex}",
        "tool_name": "get_review_history",
        "arguments": {"parent_asin": parent_asin},
        "was_allowed": True,
        "arguments_valid": bool(parent_asin),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "latency_ms": 0,
        "outcome": "success",
        "result": None,
        "error": None,
    }
    call_log.append(record)
    try:
        if _simulate_failure:
            raise RuntimeError("Simulated tool failure: review history lookup unavailable")
        by_year = _load_yearly_by_asin().get(parent_asin)
        if not by_year:
            result = f"No review history found for product ID {parent_asin}."
        else:
            lines = [
                f"- {year}: {len(ratings)} reviews, average rating "
                f"{sum(ratings) / len(ratings):.1f}"
                for year, ratings in sorted(by_year.items())
            ]
            result = "\n".join(lines)
        record["result"] = result
        return result
    except Exception as exc:
        record["outcome"] = "error"
        record["error"] = {
            "error_type": type(exc).__name__,
            "message": str(exc),
            "retryable": isinstance(exc, RuntimeError),
        }
        raise
    finally:
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
        record["latency_ms"] = round((time.perf_counter() - started_perf) * 1000)
