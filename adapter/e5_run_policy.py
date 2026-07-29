"""Experiment-level retry, sweep validity, and native sanity policy for E5."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


ERROR_RATE_LIMIT = 0.05


def run_case_attempts(run_once: Callable[[], dict[str, Any]]) -> list[dict[str, Any]]:
    """Run once, retrying exactly once only when the first verdict is ``error``."""
    attempts = [run_once()]
    if attempts[0].get("verdict") == "error":
        attempts.append(run_once())
    return attempts


def summarize_framework_sweep(
    attempts_by_case: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    """Summarize final attempts and enforce the approved five-percent guard."""
    if not attempts_by_case or any(not attempts for attempts in attempts_by_case):
        raise ValueError("each sweep case must contain at least one attempt")

    results = [attempts[-1] for attempts in attempts_by_case]
    errors = sum(result.get("verdict") == "error" for result in results)
    verdicts = [result for result in results if result.get("verdict") != "error"]
    passes = sum(result.get("verdict") == "pass" for result in verdicts)
    error_rate = errors / len(results)
    return {
        "case_count": len(results),
        "verdict_count": len(verdicts),
        "pass_count": passes,
        "error_count": errors,
        "pass_rate": passes / len(verdicts) if verdicts else None,
        "error_rate": error_rate,
        "valid": error_rate <= ERROR_RATE_LIMIT,
    }


def record_tau3_db_sanity(
    run_log: dict[str, Any],
    *,
    db_match: bool,
    db_reward: float,
) -> dict[str, Any]:
    """Attach the upstream DB-only sanity result without changing our verdict."""
    result = dict(run_log)
    sanity = dict(result.get("sanity") or {})
    tau3_db = {"db_match": db_match, "db_reward": db_reward}

    evaluation = result.get("evaluation")
    if isinstance(evaluation, dict):
        criterion_b = evaluation.get("criterion_b")
        if isinstance(criterion_b, dict) and isinstance(criterion_b.get("met"), bool):
            tau3_db["agrees_with_criterion_b"] = criterion_b["met"] == db_match

    sanity["tau3_db"] = tau3_db
    result["sanity"] = sanity
    return result
