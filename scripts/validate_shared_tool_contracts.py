#!/usr/bin/env python3
"""Offline no-tool/success/failure checks for shared local tool traces."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.runtime import normalize_tool_calls
from adapter.validation import validate_tool_call_constraints
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools


SCENARIOS = [
    (medical_tools, medical_tools.search_literature, "21550158"),
    (ecommerce_tools, ecommerce_tools.get_review_history, "B07KTB8PHS"),
]


def _validate(call: dict) -> None:
    errors = validate_tool_call_constraints(call)
    if errors:
        raise AssertionError(errors)


def main() -> None:
    assert normalize_tool_calls([], "run-no-tool") == []

    # Contract tests must not require downloaded benchmark data. Populate the
    # existing local-tool cache variables with clearly synthetic in-memory data.
    medical_tools._dataset = {
        "21550158": {"CONTEXTS": ["Synthetic abstract for tool-contract testing."]}
    }
    ecommerce_tools._yearly_by_asin = {
        "B07KTB8PHS": {2024: [4.0], 2025: [4.0, 5.0]}
    }

    success_count = 0
    failure_count = 0
    for index, (module, function, argument) in enumerate(SCENARIOS):
        module.reset_call_log()
        module.set_simulate_failure(False)
        function(argument)
        call = normalize_tool_calls(module.call_log, f"run-success-{index}")[0]
        assert call["outcome"] == "success"
        assert call["error"] is None
        _validate(call)
        success_count += 1

        module.reset_call_log()
        module.set_simulate_failure(True)
        try:
            function(argument)
        except RuntimeError:
            pass
        else:  # pragma: no cover - guard against a broken failure hook
            raise AssertionError("simulated tool failure did not raise")
        finally:
            module.set_simulate_failure(False)
        call = normalize_tool_calls(module.call_log, f"run-failure-{index}")[0]
        assert call["outcome"] == "error"
        assert call["error"] is not None
        _validate(call)
        failure_count += 1

    print(
        f"SHARED_TOOL_CONTRACTS_OK no_tool=1 success={success_count} "
        f"failure={failure_count}"
    )


if __name__ == "__main__":
    main()
