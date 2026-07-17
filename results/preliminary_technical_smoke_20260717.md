# Preliminary Technical Smoke — Not Benchmark Scores

> **Status: preliminary engineering check only.** This report does not measure
> benchmark accuracy, medical quality, safety quality, framework suitability,
> or final comparative performance. It must not be used to rank frameworks.

## Purpose

Verify that the v1 benchmark cases travel end to end through the OpenAI Agents
SDK, LangGraph, and CrewAI adapters. A baseline smoke exposed a shared medical
boolean-contract defect. The identical 21-call smoke was then repeated after a
prompt and runner-validation fix to confirm the engineering effect.

## Configuration

| Item | Value |
|---|---|
| Date | 2026-07-17 |
| Baseline experiment | `prelim-tech-smoke-20260717-d258ec2` |
| After-fix experiment | `prelim-tech-smoke-20260717-boolean-fix` |
| Repository starting commit | `d258ec2` |
| Model | `gpt-4o-mini` |
| Temperature | `0` |
| Repeats per experiment | `1` |
| Cases | `H1/H2/H4/H5/E1/E2/E3-REVIEW-001` |
| Frameworks | OpenAI Agents SDK, LangGraph, CrewAI |
| Completed calls | 21 baseline + 21 after fix = 42 |

E5 was deliberately excluded because the shared tau-retail simulator/tool
bridge is not implemented. Running E5 without that environment would test a
different task and produce misleading results.

## Before/after summary

| Check | Baseline | After fix |
|---|---:|---:|
| Runtime success | 21/21 | 21/21 |
| Valid JSON | 21/21 | 21/21 |
| Correct case/task identity | 21/21 | 21/21 |
| Strict task output schema | **12/21** | **20/21** |
| Medical strict output schema | **3/12** | **12/12** |
| Recorded tool calls | 0 | 0 |

The medical improvement directly matches the intended fix: prompts now show
literal JSON booleans and explicitly prohibit string substitutes such as
`"high"`, `"low"`, `"yes"`, and `"caution"`.

## Resolved issues

| Issue found in baseline | Fix | Verification | Status |
|---|---|---|---|
| Medical safety fields were sometimes emitted as strings instead of JSON booleans. | Added a typed JSON example and explicitly prohibited string substitutes in medical prompts. | Medical strict-schema compliance improved from 3/12 to 12/12; H1, H4, and H5 each improved from 0/3 to 3/3. | Resolved in this smoke. |
| The runner treated any valid JSON response as normal even when it violated the task-specific output schema. | Added task-to-schema validation, `output_schema_valid_rate`, schema error details, and the `output_schema_invalid` failure mode. | The runner detected the after-fix E3 response that had misplaced required fields instead of silently reporting it as `ok`. | Resolved. |
| Offline adapter checks did not exercise task-output schema validation. | Added valid, invalid, non-applicable, and evaluator failure-mode contract checks. | `validate_adapter_contracts.py` passes with `output_schema=6`. | Resolved. |

## Remaining technical issue

One after-fix E3 response from the OpenAI Agents SDK placed `explanation` and
`evidence_ids` inside `result` instead of at the required top level. The new
validator correctly reports this as `output_schema_invalid`, so this is no
longer a hidden runner problem. Structured-output enforcement or a bounded
repair policy remains future engineering work; it is not claimed as fixed in
this report. E1/E2/E3 semantic correctness also remains outside this technical
smoke and requires approved evaluator rules.

## Framework observations

| Framework | Baseline strict schema | After-fix strict schema | Baseline avg. latency | After-fix avg. latency | Baseline tokens | After-fix tokens |
|---|---:|---:|---:|---:|---:|---:|
| OpenAI Agents SDK | 4/7 | 6/7 | 9.246 s | 5.987 s | 7,587 | 7,838 |
| LangGraph | 4/7 | 7/7 | 6.982 s | 6.333 s | 7,720 | 7,958 |
| CrewAI | 4/7 | 7/7 | 8.897 s | 8.063 s | 8,321 | 8,505 |

Latency and token values are single-run observations, not comparative
estimates. Framework prompt wrappers and transient endpoint conditions affect
both measurements.

## Strict schema result by task

| Task | Baseline | After fix | Technical observation |
|---|---:|---:|---|
| H1 | 0/3 | 3/3 | All frameworks switched from string safety values to JSON booleans. |
| H2 | 3/3 | 3/3 | Remained valid; no regression. |
| H4 | 0/3 | 3/3 | All natural-language `safety_flag` strings were eliminated. |
| H5 | 0/3 | 3/3 | All `high`/`low` safety strings were replaced with booleans. |
| E1 | 3/3 | 3/3 | Remained structurally valid. |
| E2 | 3/3 | 3/3 | Remained structurally valid; semantic constraint issue remains. |
| E3 | 3/3 | 2/3 | One OpenAI Agents SDK output nested top-level fields inside `result`; the new runner detected it. |

## What changed in the infrastructure

- Medical task prompts now include a typed safety example:
  `{"safety_flag":true,"recommend_professional_care":true,"safety_note":"..."}`.
- `adapter.validation.validate_task_output` maps H1/H2/H4/H5 to the medical
  schema and E1/E2/E3/E5 to the e-commerce schema.
- The normal runner now reports `output_schema_valid_rate` separately from
  `json_valid_rate`.
- `output_schema_invalid` is now a first-class failure mode rather than being
  silently counted as `ok`.
- Offline contract checks cover one valid, one invalid, and one non-applicable
  output-schema case.

The after-fix E3 formatting drift demonstrates why the runner change matters:
the response was valid JSON with correct case/task identity, but it omitted
top-level `explanation` and `evidence_ids` because those fields were placed
inside `result`. The old summary would have reported it as normal; the new
summary correctly reported `output_schema_valid_rate=0%` and
`output_schema_invalid`.

## Non-scoring semantic observations

These observations guide later evaluator work and are not accuracy results.

- **E1:** outputs continued to explain average rating more than review volume,
  while the converter's trend direction is defined from review volume.
- **E2:** in both runs, LangGraph and CrewAI each included one product below
  the `4.0` minimum while returning `constraints_satisfied: true`. Strict JSON
  Schema cannot detect this cross-field semantic inconsistency.
- **E3:** in both runs, OpenAI Agents SDK and LangGraph selected
  `return_allowed`, while CrewAI selected `refund_allowed`. No correctness
  conclusion is made while E3 mapping semantics remain under owner review.
- **Tools:** all 42 runs recorded zero tool calls. The selected seven cases
  embed their required evidence; E5 was excluded.

## Limitations

- One case per task and one repeat provide no estimate of variance.
- H2 lower-urgency and H4 extraction review are not owner-approved.
- H5 covers only a source-derived refusal sample, not clarify/escalate cases.
- E5 and all real tau-retail state mutations are absent.
- No gold accuracy, rubric score, safety score, or final-state score was run.
- All frameworks used the same underlying model; this checks adapter behavior,
  not different model capabilities.
- Raw prompts, raw HealthBench records/canaries, evaluator-only gold, API
  configuration, and raw outputs are not included in this report.

## Recommended next engineering checks

1. Consider structured-output enforcement or one bounded repair attempt for
   misplaced fields such as the after-fix E3 response; report repaired and
   unrepaired validity separately.
2. Add evaluator checks for E1 target-signal grounding and E2 constraint
   consistency after dataset semantics are approved.
3. Repeat this technical smoke with more cases/repeats only after owner review;
   do not treat expanded technical checks as benchmark scores.
4. Do not run E5 until the shared simulator and framework wrappers exist.

## Conclusion

The targeted prompt fix removed all observed medical output-schema failures in
the repeat smoke, improving overall strict contract compliance from 12/21 to
20/21. The strict runner integration also caught a separate E3 formatting drift
that generic JSON validation missed. These are useful engineering results, but
they remain explicitly **not benchmark scores or framework rankings**.
