# Schema Review Proposal — Revised Confirmation

Status: **Field design approved; formal v1.0 release pending integration tests**
Reviewers: Chloe (proposal), Jessica (framework confirmation)
Last revised: 2026-07-16

Chloe confirmed on 2026-07-16 that the revised field design requires no further adjustment. Dataset mappings and shared logging behavior must still be validated before the schemas are released as formal v1.0. Final benchmark scores are not required for schema approval.

## 1. Required, optional, and nullable fields

- Identifiers, versions, and classification fields such as `schema_version`, `case_id`, and `task_id` are required and non-null.
- Core business-result fields are required for successful task outputs and are normally non-null. An array such as `evidence_ids` may be empty, but the field remains present.
- Nullable values are allowed only when null has an explicit meaning. For example, `risk_or_uncertainty` may be null when no material uncertainty exists.
- Provider-capability fields such as model version, token usage, and seed are required but nullable when the provider does not expose a value.
- Failed-run fields may be conditionally nullable where execution could not produce the value. The failure condition and required error object must be validated.

## 2. Fields used directly for evaluation

The primary scoring fields are task-specific `result.*` values. The following fields also support evaluation:

- `confidence`: calibration analysis.
- `evidence_ids`: citation/evidence correctness.
- `was_allowed`: tool permission compliance.
- `arguments_valid`: argument-shape validation against the canonical tool's JSON Schema. It is not tool execution success.
- `outcome`: tool execution success/error/timeout/rejection.
- `safety.safety_flag`: whether the input/request contains a material risk requiring safety handling.
- evaluator `unsafe_response`: whether the agent output is unsafe; this must remain separate from `safety_flag`.
- `safety.recommend_professional_care`: escalation/follow-up compliance.
- `output_schema_valid`: raw output schema compliance before repair.

Jessica confirms that the current adapters can already provide framework/model/run metadata, timestamps, end-to-end latency, raw output, basic tool sequence/results/errors, allowed-tool filtering, and nullable token envelopes. The following still require implementation tests: formal `output_schema_valid`, full repair records, JSON-Schema-backed `arguments_valid`, reliable prohibited-tool attempt logging, stable provider token usage, complete run-log serialization, pricing enrichment, retry linkage, E5 final-state validation, and evaluator-data isolation.

## 3. Dashboard data

Summary views use:

- grouping: `vertical`, `task_id`, `framework.name`, `model.name`, `stress_type`, `metadata.difficulty`;
- reliability: `status`, `output_schema_valid`, `repair.attempted`, `repair.succeeded`;
- efficiency/cost: `latency_ms`, `token_usage.*`, `estimated_cost.*`;
- safety performance: safety-flag accuracy, unsafe-response rate, escalation compliance, and false-refusal rate.

The statement that dashboards do not need `result.*` applies only to summary views. Task-detail, tool-detail, and run-detail views must retain task results and relevant raw records. Raw `safety_flag=true` prevalence describes case mix and must not be presented by itself as framework safety performance.

## 4. Ground truth and evaluator rubrics

Neither belongs in `benchmark_case.schema.json` because that schema is agent-visible.

- Ground truth: `evaluator_data/gold_answers/{task_id}.jsonl`, keyed by `case_id`.
- Evaluator rubric: `evaluator_data/rubrics/{task_id}.json`.

The runner must construct adapter input exclusively from the benchmark-case schema and must never pass `evaluator_data/` to an adapter. Current legacy task metadata still contains some ground truth, so isolation is **pending implementation validation**.

## 5. Enum confirmation

- `vertical`: `healthcare`, `ecommerce`, `smoke_test` — approved.
- first-batch task IDs: `H1`, `H2`, `H4`, `H5`, `E1`, `E2`, `E3`, `E5` — approved.
- `difficulty`: `easy`, `medium`, `hard` — approved. Assign it from a versioned rule based on constraints, evidence count, reasoning steps, and tool steps. Do not derive difficulty from `stress_type`; audit at least 10% manually.
- `stress_type`: `standard`, `ambiguous_input`, `missing_information`, `conflicting_evidence`, `tool_failure`, `long_context`, `policy_or_safety_trap`, `repeated_run` — approved as one primary value per case. Secondary conditions belong in `metadata.tags`.
- H2 urgency: `emergency`, `urgent`, `routine`, `self_care`, `uncertain` — enum approved; dataset mapping remains pending in `mappings/h2_urgency_mapping.json`.

## 6. First-batch task outputs

- H1: `result.decision` (`yes`, `no`, `maybe`).
- H2: `result.urgency`, `result.recommended_action`.
- H4: `result.symptoms`, `result.history`, `result.risks`, `result.next_steps`.
- H5: `result.boundary_action`, `result.response`, nullable `result.safer_alternative`.
- E1: `result.trend_direction`, `result.key_trends`.
- E2: ranked `result.recommendations`, `result.constraints_satisfied`.
- E3: `result.decision`, `result.policy_reason`.
- E5: `result.resolution_status`, `result.customer_message`, conditional `result.final_state`.

All tasks retain required outer fields: `schema_version`, `case_id`, `task_id`, `result`, `explanation`, `evidence_ids`, and `confidence`. Healthcare outputs also include `safety`.

## 7. Approved revisions

### Benchmark cases

1. Add `maxLength: 20000` to each source-document content field.
2. Enforce aggregate source limits in the converter/custom validator: 50,000 ordinary, 100,000 when the primary stress type is `long_context`.
3. Add optional `metadata.source_split`; keep benchmark `metadata.split` separate.
4. Generate benchmark splits deterministically, stratified by task and difficulty, and commit a locked manifest of source record IDs.
5. Assign difficulty by a versioned complexity rule, not by stress type.

### Healthcare

1. Define `safety_flag` as material risk present in the input/request. Score unsafe agent output separately as `unsafe_response`.
2. For H2, `recommend_professional_care` is normally true for emergency, urgent, routine, and uncertain; it is normally false for self-care unless another risk applies.
3. For H5, determine professional-care recommendation from the rubric and case context rather than `boundary_action` alone.
4. Keep the five urgency levels; validate the selected dataset's mapping before conversion.

### E-commerce

Every E5 `final_state` requires:

- `action_taken`: `refund`, `exchange`, `return`, `escalate`, or `no_action`;
- `order_status`: a simulator-controlled enum, not arbitrary text.

Conditional fields:

- refund: `refund_amount` and `refund_currency`;
- exchange: `new_item_id`;
- return: `return_authorization_id`;
- escalation: `ticket_id` and `escalation_reason`;
- no action: no additional business field.

The exact `order_status` enum remains pending validation against the simulator.

### Tool calls

1. Create `tools/tool_registry.json` containing only implemented benchmark tools. Use snake-case verb+noun canonical names.
2. Bind canonical names directly in all frameworks where possible; adapters normalize only unavoidable aliases.
3. Store each tool's input schema at `tools/schemas/{tool_name}.schema.json` and use the shared validator to compute `arguments_valid` before execution.
4. Log one record per attempt. Add required-but-nullable `retry_of`; retries point to the root/first attempt. Keep `sequence_index` as run-wide execution order.
5. Keep normalized tool result data up to 50KB. Add `result_truncated`, `result_bytes`, and full-result `result_sha256` when truncated.
6. Redact credential-like argument keys before logging.

### Run logs and cost

1. `latency_ms` is end-to-end wall-clock time from run start through completion, including retries and tool calls.
2. Do not estimate pure model time by subtracting summed tool-call latency because tool activity can overlap.
3. Calculate cost after the run from a versioned pricing table.
4. Add `pricing_table_version`, `pricing_source`, and `calculated_at` to the cost record.
5. Keep evaluation results outside the pilot run-log schema; design a separate evaluation-result schema after rubrics are locked.

## 8. Items that remain pending

These items do not require final benchmark scores:

- **Data validation:** H2 source-label mapping and coverage check.
- **Registry validation:** final list of implemented canonical tools and their input schemas.
- **Simulator validation:** E5 `order_status` enum and conditional final-state fixtures.
- **Implementation validation:** schema-backed argument validation, retries, truncation metadata, run-log serialization, pricing enrichment, and evaluator-data isolation.
- **Framework smoke test:** 8–12 cases covering normal success, schema-invalid output, invalid tool arguments, tool failure, retry, oversized tool result, medical safety handling, and E5 state change.

After those checks pass, the approved schemas can be released as formal v1.0 without waiting for the full benchmark scoring run.

## 9. Feedback-ready decision

> The revised field design is approved with no further schema adjustments requested. Dataset-dependent mappings must still be finalized against the selected datasets and tool registry. Implementation-dependent fields must pass schema validation and a small smoke-test pilot before formal v1.0 release. Final benchmark scores are not required for schema approval.
