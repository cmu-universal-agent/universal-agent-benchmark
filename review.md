# Code Review Findings and Fixes

Summary of the three findings from `/code-review` on this branch, the fix applied for each, and the commit that landed it.

| # | File / Line | Finding | Fix | Commit |
|---|---|---|---|---|
| 1 | `adapter/runtime.py:125` | `resolve_generation_settings()` used exact float inequality (`!=`) to flag a requested generation setting as "unsupported," so a wrapper round-tripping a value like `0.7` through its own float/pydantic coercion into `0.6999999999999998` was wrongly marked unsupported. | Added `_generation_value_matches()`, comparing floats with `math.isclose(abs_tol=1e-9)` while keeping exact comparison for int fields. Added direct unit tests for both the round-trip-noise case and a genuinely dropped setting. | `15ab762` |
| 2 | `adapter/validation.py:19` | `EVALUATOR_ONLY_KEYS` enforced a 20-word case-insensitive blocklist — including generic words like `note`, `evaluation`, `expected`, `gold`, `rubric` — as a hard, blocking gate at task-load time for every schema-v1.0 case across all three frameworks. | Split the list into `STRICT_EVALUATOR_ONLY_KEYS` (unambiguous, compound terms — still hard-blocks at runtime load) and `AMBIGUOUS_EVALUATOR_ONLY_KEYS` (common dictionary words — still flagged by the offline dataset reviewer, `scripts/validate_core_pilot.py`, but no longer crashes every framework's task load on a word collision). | `e8dc016` |
| 3 | `frameworks/crewai_agent/run.py:150` | The entire `run_task` control flow (pre-build timing capture, model-construction error handling, `begin_run`/`finish_run` wiring, tool-log reset, early-return-on-model-error, try/except around the agent run) was duplicated nearly verbatim across `frameworks/crewai_agent/run.py`, `frameworks/langgraph_agent/run.py`, and `frameworks/openai_agents_sdk/run.py`. | Extracted the shared control flow into `run_framework_task()` in `adapter/runtime.py`. Each adapter's `run_task()` now only supplies framework-specific `build_model`/`run_model` closures; `configured_generation_settings()` stays called from each framework module so existing per-framework test mocking still works. | `3bd2a1e` |

## Verification

All three fixes were verified by running the full offline test suite (`python -m unittest discover -s tests`) in each of the three framework-specific virtual environments:

- `.venv-crewai`
- `.venv-langgraph`
- `.venv-openai`

Each venv ran **45 tests with zero failures**, only the expected skips for the other two frameworks not being installed in that environment. No regressions were observed.
