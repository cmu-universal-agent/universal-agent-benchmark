# Schema Field Review

## Purpose

This document is used to review and approve the shared schemas before they are frozen for pilot testing.

The review has two owners:

- **Chloe - Evaluation owner:** confirms that the fields support scoring, analysis, and dashboard requirements.
- **Jessica - Framework owner:** confirms that LangGraph, CrewAI, and the OpenAI Agents SDK can produce or record the fields consistently.

Mickey provides final integration approval after the open decisions are resolved.

## Current Status

| Item | Status |
|---|---|
| Benchmark Case Schema | Draft for review |
| Healthcare Output Schema | Draft for review |
| E-commerce Output Schema | Draft for review |
| Tool-Call Schema | Draft for review |
| Run Log Schema | Draft for review |
| Formal schema validation tests | Validator implemented; task migration pending |
| Framework integration tests | Dual-format loader implemented; live v1 run pending |
| Schema frozen for pilot | No |

Although the schema files currently contain `schema_version: 1.0`, they should be treated as drafts until this review is complete.

### Implementation That Can Proceed Before Sign-Off

The following compatibility work does not freeze any pending field decision:

- Legacy task files remain runnable without modification.
- Schema v1.0 files are loaded through a shared converter rather than separate
  framework-specific loaders.
- `healthcare` and `ecommerce` are mapped internally to the current runtime
  vertical names until the naming decision is finalized.
- `allowed_tools` is enforced consistently; an empty list exposes no tools.
- `scripts/validate_tasks.py` reports legacy-compatible, valid v1.0, and invalid
  files separately.
- Dataset preparation supports `--cache-only` and requires explicit
  `--overwrite` before replacing existing task files.

Still pending Chloe's review: final required/optional decisions, difficulty and
stress labels, ground-truth storage, dashboard mappings, and the migration of
the existing 20 pilot tasks.

## Review Instructions

For each field, confirm:

1. Is the meaning clear?
2. Is the field required, optional, or nullable?
3. Which component produces the field?
4. Which metric, analysis, or dashboard view uses it?
5. Can all three frameworks provide it under the same conditions?
6. Could it expose a hidden answer, credential, or sensitive information?

Use the following decision values:

- `Keep`
- `Modify`
- `Remove`
- `Pending`

## 1. Benchmark Case Schema Review

File: `schemas/benchmark_case.schema.json`

This schema contains only information that may be provided to the agent. Ground-truth answers and evaluator rubrics must be stored separately.

| Field | Required | Produced by | Purpose | Evaluation use | Framework availability | Decision | Notes |
|---|---:|---|---|---|---|---|---|
| `schema_version` | Yes | Dataset converter | Tracks case-format changes | Reproducibility | Same for all | Pending | Proposed value: `1.0` |
| `case_id` | Yes | Dataset converter | Unique case identifier | Joins case, output, and log | Same for all | Pending | Example: `H1-001` |
| `task_id` | Yes | Dataset converter | Identifies benchmark task | Task-level metrics | Same for all | Pending | Core tasks: H1, H2, H4, H5, E1, E2, E3, E5 |
| `vertical` | Yes | Dataset converter | Identifies industry vertical | Vertical-level comparison | Same for all | Pending | Healthcare, e-commerce, or smoke test |
| `input.instruction` | Yes | Task designer | Instruction shown to the agent | Prompt consistency | Same for all | Pending | Must not contain the gold answer |
| `input.data` | Yes | Dataset converter | Task-specific input data | Main task input | Same for all | Pending | May contain question, context, policy, order, or product data |
| `input.source_documents` | No | Dataset converter | Agent-visible evidence | Evidence and citation scoring | Same for all | Pending | Confirm whether E3/E5 need this field |
| `source_documents[].source_id` | Yes when sources exist | Dataset converter | Citation identifier | Evidence correctness | Same for all | Pending | IDs must be stable and unique within a case |
| `source_documents[].title` | No | Dataset converter | Human-readable source title | Reporting only | Same for all | Pending | May be omitted when unavailable |
| `source_documents[].content` | Yes when sources exist | Dataset converter | Evidence content | Factuality and evidence use | Same for all | Pending | Confirm context-length limits |
| `source_documents[].published_at` | No | Dataset converter | Source timestamp | Recency and trend analysis | Same for all | Pending | Mainly relevant to E1 |
| `allowed_tools` | Yes | Task designer | Limits permitted tools | Tool overuse and policy scoring | Same for all | Pending | Empty array means no tools allowed |
| `stress_type` | Yes | Task designer | Labels the primary stress condition | Stress-test comparison | Same for all | Pending | Confirm whether one case may have multiple stress labels |
| `metadata.dataset` | Yes | Dataset converter | Records source dataset | Reproducibility | Same for all | Pending | Example: PubMedQA |
| `metadata.source_record_id` | No | Dataset converter | Links to the original record | Audit and traceability | Same for all | Pending | Avoid storing sensitive IDs |
| `metadata.split` | Yes | Dataset converter | Development/pilot/test split | Leakage control | Same for all | Pending | Test cases must remain separated |
| `metadata.difficulty` | Yes | Task designer | Difficulty label | Difficulty analysis | Same for all | Pending | Confirm how difficulty will be assigned |
| `metadata.language` | Yes | Dataset converter | Language tag | Language-level analysis | Same for all | Pending | Example: `en`, `zh-CN` |
| `metadata.tags` | No | Task designer | Additional case labels | Filtering and analysis | Same for all | Pending | Avoid duplicating `stress_type` |
| `metadata.created_at` | No | Dataset converter | Case creation timestamp | Audit only | Same for all | Pending | Confirm whether needed |

### Benchmark Case Decisions Required

- [ ] Confirm whether `stress_type` should allow one value or multiple values.
- [ ] Confirm the final list of supported verticals.
- [ ] Confirm the final metadata split names.
- [ ] Define how `difficulty` will be assigned.
- [ ] Define maximum source-document and context sizes.
- [ ] Confirm that gold answers will be stored in separate files.
- [ ] Confirm that adapters will receive only agent-visible fields.

## 2. Healthcare Output Schema Review

File: `schemas/medical_output.schema.json`

| Field | Required | Produced by | Purpose | Evaluation use | Framework availability | Decision | Notes |
|---|---:|---|---|---|---|---|---|
| `schema_version` | Yes | Agent/adapter | Tracks output-format changes | Reproducibility | Must be the same | Pending | Proposed value: `1.0` |
| `case_id` | Yes | Agent/adapter | Links output to case | Consistency check | Must be the same | Pending | Runner may inject this if needed |
| `task_id` | Yes | Agent/adapter | Selects task-specific result | Task scoring | Must be the same | Pending | H1, H2, H4, or H5 |
| `result` | Yes | Agent | Contains task-specific answer | Primary task scoring | Must be supported | Pending | Defined separately for each task |
| `explanation` | Yes | Agent | Concise user-facing explanation | Quality and factuality | Must be supported | Pending | Must not request hidden chain-of-thought |
| `evidence_ids` | Yes | Agent | Identifies supporting sources | Citation correctness | Must be supported | Pending | Confirm whether empty arrays are acceptable |
| `confidence` | Yes | Agent | Self-reported certainty | Calibration analysis | Must be supported | Pending | Range: 0 to 1 |
| `safety.safety_flag` | Yes | Agent | Flags material medical risk | Safety evaluation | Must be supported | Pending | Define exact meaning of `true` |
| `safety.recommend_professional_care` | Yes | Agent | Indicates escalation | Escalation compliance | Must be supported | Pending | Important for uncertain or high-risk cases |
| `safety.safety_note` | Yes | Agent | Provides explicit safety language | Literal schema and safety checks | Must be supported | Pending | `safe_note` must fail raw schema validation |

### H1 - Evidence-Based Medical QA

| Field | Required | Proposed values | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.decision` | Yes | `yes`, `no`, `maybe` | Answer accuracy | Pending | Must match dataset label |

### H2 - Symptom Triage Safety

| Field | Required | Proposed values | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.urgency` | Yes | `emergency`, `urgent`, `routine`, `self_care`, `uncertain` | Triage accuracy | Pending | Confirm alignment with selected dataset |
| `result.recommended_action` | Yes | Free text | Safety and action quality | Pending | May require rubric-based scoring |

### H4 - Clinical Note Summarization

| Field | Required | Proposed format | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.symptoms` | Yes | String array | Completeness | Pending | Confirm whether empty is allowed |
| `result.history` | Yes | String array | Completeness | Pending | Confirm whether medication history is separate |
| `result.risks` | Yes | String array | Risk capture | Pending | Confirm definition of risk |
| `result.next_steps` | Yes | String array | Action completeness | Pending | Must avoid presenting unsupported diagnosis |

### H5 - Refusal and Boundary Handling

| Field | Required | Proposed values | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.boundary_action` | Yes | `comply`, `refuse`, `clarify`, `escalate` | Refusal appropriateness | Pending | Confirm whether multiple actions may apply |
| `result.response` | Yes | Free text | Response quality | Pending | Must be safe and user-facing |
| `result.safer_alternative` | Yes, nullable | Free text or null | Helpful redirection | Pending | Define when null is acceptable |

### Healthcare Decisions Required

- [ ] Confirm whether every healthcare task requires `evidence_ids`.
- [ ] Confirm whether every healthcare task requires `confidence`.
- [ ] Confirm the H2 urgency categories against the selected dataset.
- [ ] Confirm whether H4 needs additional sections such as medications or allergies.
- [ ] Define when `recommend_professional_care` must be true.
- [ ] Define when `safety_flag` must be true.
- [ ] Confirm that raw `safe_note` output is recorded as schema-invalid rather than silently corrected.
- [ ] Define which healthcare fields use exact scoring and which require a rubric.

## 3. E-commerce Output Schema Review

File: `schemas/ecommerce_output.schema.json`

| Field | Required | Produced by | Purpose | Evaluation use | Framework availability | Decision | Notes |
|---|---:|---|---|---|---|---|---|
| `schema_version` | Yes | Agent/adapter | Tracks output-format changes | Reproducibility | Must be the same | Pending | Proposed value: `1.0` |
| `case_id` | Yes | Agent/adapter | Links output to case | Consistency check | Must be the same | Pending | Runner may inject this if needed |
| `task_id` | Yes | Agent/adapter | Selects task-specific result | Task scoring | Must be the same | Pending | E1, E2, E3, or E5 |
| `result` | Yes | Agent | Contains task-specific answer | Primary task scoring | Must be supported | Pending | Defined separately for each task |
| `explanation` | Yes | Agent | Business explanation | Quality and factuality | Must be supported | Pending | Keep concise |
| `evidence_ids` | Yes | Agent | Identifies supporting records | Evidence correctness | Must be supported | Pending | Confirm whether E3/E5 require evidence IDs |
| `confidence` | Yes | Agent | Self-reported certainty | Calibration analysis | Must be supported | Pending | Range: 0 to 1 |
| `risk_or_uncertainty` | Yes, nullable | Agent | Records limitations | Uncertainty quality | Must be supported | Pending | Define when null is acceptable |

### E1 - Product Trend Research

| Field | Required | Proposed values | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.trend_direction` | Yes | `increasing`, `decreasing`, `stable`, `mixed`, `insufficient_evidence` | Trend accuracy | Pending | Confirm scoring for mixed trends |
| `result.key_trends` | Yes | String array | Insight coverage | Pending | Confirm required number of trends |

### E2 - Product Recommendation

| Field | Required | Proposed format | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.recommendations` | Yes | Ranked product array | Relevance | Pending | Between 1 and 20 recommendations |
| `recommendations[].product_id` | Yes | String | Product validity | Pending | Must exist in the supplied catalogue |
| `recommendations[].rank` | Yes | Integer | Ranking quality | Pending | Check for duplicate ranks separately |
| `recommendations[].rationale` | Yes | Free text | Explanation quality | Pending | Must cite relevant constraints |
| `result.constraints_satisfied` | Yes | Boolean | Constraint satisfaction | Pending | Evaluator must verify independently |

### E3 - Return and Refund Policy Decision

| Field | Required | Proposed values | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.decision` | Yes | `refund_allowed`, `exchange_allowed`, `return_allowed`, `not_allowed`, `needs_review` | Policy accuracy | Pending | Confirm whether decisions are mutually exclusive |
| `result.policy_reason` | Yes | Free text | Policy evidence quality | Pending | Consider adding policy IDs if needed |

### E5 - Customer Support Tool Use

| Field | Required | Proposed values | Metric | Decision | Notes |
|---|---:|---|---|---|---|
| `result.resolution_status` | Yes | `resolved`, `partially_resolved`, `unresolved`, `escalated` | Task success | Pending | Define status mapping |
| `result.customer_message` | Yes | Free text | User-facing quality | Pending | Must match actual environment state |
| `result.final_state` | Yes | Object | Final-state correctness | Pending | Evaluator must compare it with environment state |

### E-commerce Decisions Required

- [ ] Confirm whether every e-commerce task requires `evidence_ids`.
- [ ] Confirm whether every e-commerce task requires `confidence`.
- [ ] Confirm E1 trend-direction categories.
- [ ] Define how E2 recommendation relevance will be scored.
- [ ] Confirm whether E3 decisions are mutually exclusive.
- [ ] Decide whether E3 needs explicit policy IDs.
- [ ] Define the required structure of E5 `final_state`.
- [ ] Define which fields use exact scoring and which require a rubric.

## 4. Tool-Call Schema Review

File: `schemas/tool_call.schema.json`

| Field | Required | Produced by | Purpose | Evaluation use | Framework availability | Decision | Notes |
|---|---:|---|---|---|---|---|---|
| `schema_version` | Yes | Runner | Tracks tool-log format | Reproducibility | Same for all | Pending | Proposed value: `1.0` |
| `tool_call_id` | Yes | Runner | Unique call identifier | Traceability | Same for all | Pending | Runner-generated ID recommended |
| `run_id` | Yes | Runner | Links call to execution | Run analysis | Same for all | Pending | Must match run log |
| `sequence_index` | Yes | Runner | Records call order | Workflow analysis | Same for all | Pending | Starts at zero |
| `tool_name` | Yes | Adapter | Identifies selected tool | Tool selection accuracy | Must be normalized | Pending | Use shared benchmark tool names |
| `arguments` | Yes | Adapter | Records tool parameters | Argument accuracy | Must be captured | Pending | Confirm redaction rules |
| `was_allowed` | Yes | Runner/evaluator | Checks case permission | Tool overuse/policy violation | Same for all | Pending | False is a valid log value but an evaluation failure |
| `arguments_valid` | Yes | Tool wrapper | Input validation result | Tool-call success | Same for all | Pending | Requires tool input schemas |
| `started_at` | Yes | Tool wrapper | Start timestamp | Latency calculation | Same for all | Pending | UTC recommended |
| `completed_at` | Yes, nullable | Tool wrapper | Completion timestamp | Latency and timeout analysis | Same for all | Pending | Null when execution never completed |
| `latency_ms` | Yes | Tool wrapper | Tool execution time | Efficiency | Same for all | Pending | Use integer milliseconds |
| `outcome` | Yes | Tool wrapper | Execution result category | Tool reliability | Same for all | Pending | Success, error, timeout, rejected |
| `result` | Yes, may be null | Tool wrapper | Normalized raw result | Audit and recovery analysis | Must be normalized | Pending | Confirm whether to store full results or summaries |
| `error` | Yes, nullable | Tool wrapper | Structured failure information | Failure analysis | Same for all | Pending | Required when outcome is not success |

### Tool-Call Decisions Required

- [ ] Define the shared names of all benchmark tools.
- [ ] Decide whether full tool results may be logged.
- [ ] Define credential and sensitive-data redaction rules.
- [ ] Confirm whether tool-call sequence numbering starts at zero.
- [ ] Define tool input schemas needed for `arguments_valid`.
- [ ] Confirm how framework-internal retries will be represented.

## 5. Run Log Schema Review

File: `schemas/run_log.schema.json`

| Field | Required | Produced by | Purpose | Evaluation use | Framework availability | Decision | Notes |
|---|---:|---|---|---|---|---|---|
| `schema_version` | Yes | Runner | Tracks log-format changes | Reproducibility | Same for all | Pending | Proposed value: `1.0` |
| `run_id` | Yes | Runner | Unique execution identifier | Traceability | Same for all | Pending | Must be unique |
| `experiment_id` | Yes | Runner/config | Groups comparable runs | Experiment comparison | Same for all | Pending | One experiment should use one fixed model configuration |
| `case_id` | Yes | Runner | Links run to case | Case-level analysis | Same for all | Pending | Must match case |
| `task_id` | Yes | Runner | Identifies task | Task metrics | Same for all | Pending | Must match case |
| `vertical` | Yes | Runner | Identifies vertical | Vertical comparison | Same for all | Pending | Must match case |
| `framework.name` | Yes | Adapter/config | Identifies framework | Main comparison | Same for all | Pending | LangGraph, CrewAI, or OpenAI Agents SDK |
| `framework.version` | Yes | Adapter/config | Records installed version | Reproducibility | Must be captured | Pending | Do not infer later from requirements files |
| `framework.adapter_version` | No | Adapter/config | Tracks wrapper changes | Debugging | Same for all | Pending | Git commit may be better |
| `model.provider` | Yes | Config | Identifies model provider | Model-effect control | Same for all | Pending | Required due to pilot model mixing |
| `model.name` | Yes | Config | Identifies exact model | Model-effect control | Same for all | Pending | Never generate reports without this field |
| `model.version` | No | Config | Records dated model version | Reproducibility | Depends on provider | Pending | Use null when unavailable |
| `model.base_url_label` | No | Config | Identifies endpoint without secrets | Audit | Same for all | Pending | Must not contain credentials |
| `generation_config.temperature` | Yes | Config | Records sampling setting | Fairness control | Same for all | Pending | Must be fixed in main experiment |
| `generation_config.max_output_tokens` | Yes, nullable | Config | Records output limit | Fairness and failure analysis | Depends on provider | Pending | Decide whether null is acceptable |
| `generation_config.seed` | Yes, nullable | Config | Records random seed | Reproducibility | Depends on provider | Pending | Null when unsupported |
| `prompt_version` | Yes | Config | Tracks prompt changes | Reproducibility | Same for all | Pending | Prompt content should be stored separately |
| `case_schema_version` | Yes | Runner | Records input schema | Reproducibility | Same for all | Pending | Expected: `1.0` |
| `output_schema_version` | Yes | Runner | Records output schema | Reproducibility | Same for all | Pending | Expected: `1.0` |
| `started_at` | Yes | Runner | Execution start | Audit | Same for all | Pending | UTC recommended |
| `completed_at` | Yes, nullable | Runner | Execution completion | Audit and timeout analysis | Same for all | Pending | Null when unfinished |
| `latency_ms` | Yes | Runner | End-to-end runtime | Latency comparison | Same for all | Pending | Define whether retries are included |
| `status` | Yes | Runner | Run outcome | Reliability | Same for all | Pending | Success, partial, or failed |
| `raw_output` | Yes, nullable | Adapter | Preserves original output | Schema-drift analysis | Must be captured | Pending | Never overwrite with repaired output |
| `parsed_output` | Yes, nullable | Parser | Stores parsed JSON | Output analysis | Same for all | Pending | Must represent pre-repair parsing |
| `output_schema_valid` | Yes | Validator | Raw schema result | Schema-compliance metric | Same for all | Pending | False for `safe_note` typo |
| `repair.attempted` | Yes | Repair layer | Records repair attempt | Recovery analysis | Same for all | Pending | Apply identical repair rules |
| `repair.succeeded` | Yes, nullable | Repair layer | Records repair success | Recovery analysis | Same for all | Pending | Null when not attempted |
| `repair.repaired_output` | Yes, nullable | Repair layer | Stores repaired JSON | Post-repair evaluation | Same for all | Pending | Must not replace raw output |
| `repair.changes` | Yes | Repair layer | Describes modifications | Audit | Same for all | Pending | Example: renamed `safe_note` |
| `tool_calls` | Yes | Adapter/tool wrapper | Stores normalized calls | Tool-use evaluation | Must be normalized | Pending | Uses Tool-Call Schema |
| `token_usage.input_tokens` | Yes, nullable | Provider/adapter | Input usage | Cost and efficiency | Provider-dependent | Pending | Null when unavailable |
| `token_usage.output_tokens` | Yes, nullable | Provider/adapter | Output usage | Cost and efficiency | Provider-dependent | Pending | Null when unavailable |
| `token_usage.total_tokens` | Yes, nullable | Provider/adapter | Total usage | Cost and efficiency | Provider-dependent | Pending | Check arithmetic when values exist |
| `estimated_cost.amount` | Yes, nullable | Runner | Estimated run cost | Cost comparison | Same calculation | Pending | Requires a versioned pricing table |
| `estimated_cost.currency` | Yes | Runner/config | Cost currency | Reporting | Same for all | Pending | Proposed: USD |
| `evaluation` | No | Evaluator | Stores metric results | Reporting | Same evaluator | Pending | Consider a separate evaluation schema later |
| `error` | Yes, nullable | Runner/adapter | Structured failure | Failure analysis | Same for all | Pending | Required when status is failed |

### Run Log Decisions Required

- [ ] Confirm that every report must group results by both framework and model.
- [ ] Confirm whether model version is mandatory when available.
- [ ] Confirm whether adapter version or Git commit should be recorded.
- [ ] Define end-to-end latency boundaries.
- [ ] Define whether latency includes retries and tool calls.
- [ ] Confirm null handling for token usage and cost.
- [ ] Define the cost calculation source and pricing-table version.
- [ ] Decide whether evaluation results belong in the run log or a separate file.
- [ ] Define one common output-repair policy for all frameworks.
- [ ] Confirm that API keys and credentials must never be logged.

## 6. Cross-Schema Consistency Checks

These checks cannot be enforced completely by validating one JSON file at a time. The benchmark runner or evaluator must verify them.

| Check | Expected rule | Owner | Status |
|---|---|---|---|
| Case/output `case_id` | Must match | Runner | Pending |
| Case/output `task_id` | Must match | Runner | Pending |
| Case/run-log `vertical` | Must match | Runner | Pending |
| Output schema selection | Healthcare cases use healthcare output; e-commerce cases use e-commerce output | Runner | Pending |
| Evidence IDs | Every output evidence ID exists in the case sources or tool results | Evaluator | Pending |
| Allowed tools | Every called tool is compared with `allowed_tools` | Evaluator | Pending |
| Tool/run `run_id` | Must match | Runner | Pending |
| Framework configuration | Logged framework and version match the actual adapter | Adapter | Pending |
| Model configuration | Logged model matches the actual request | Adapter | Pending |
| Token totals | Total equals input plus output when all values exist | Evaluator | Pending |
| Gold-answer isolation | Agent-visible prompt contains no expected answer or evaluator rubric | Runner/test | Pending |

## 7. Required Test Fixtures After Review

After the fields are approved, create the following minimum fixtures:

### Valid Fixtures

- One valid healthcare benchmark case
- One valid e-commerce benchmark case
- One valid H1 output
- One valid H2 output
- One valid H4 output
- One valid H5 output
- One valid E1 output
- One valid E2 output
- One valid E3 output
- One valid E5 output
- One successful tool-call record
- One failed tool-call record
- One successful run log
- One failed run log

### Invalid Fixtures

- Case missing `case_id`
- Case containing a forbidden `expected` field
- Healthcare output with `decision: probably`
- Healthcare output with `confidence: 1.5`
- Healthcare output using `safe_note` instead of `safety_note`
- E-commerce output using the wrong task result structure
- Tool call missing `run_id`
- Successful tool call containing an error object
- Run log missing `model.name`
- Run log missing `raw_output`
- Failed run log without an error object

## 8. Approval Criteria

The schemas may be frozen for pilot testing only when:

- [ ] Chloe confirms that all required metrics and dashboard views are supported.
- [ ] Jessica confirms that all three framework adapters can produce the required runtime fields.
- [ ] Mickey confirms that the schemas integrate with the shared runner.
- [ ] All open field decisions are resolved.
- [ ] Valid fixtures pass schema validation.
- [ ] Invalid fixtures fail for the expected reason.
- [ ] Cross-schema consistency checks are implemented or assigned.
- [ ] Gold answers are stored separately and cannot be sent to agents.
- [ ] Model name is recorded for every run.
- [ ] Raw and repaired outputs are stored separately.

## 9. Final Sign-Off

| Role | Name | Decision | Date | Notes |
|---|---|---|---|---|
| Evaluation owner | Chloe | Pending |  |  |
| Framework owner | Jessica | Pending |  |  |
| Integration owner | Mickey | Pending |  |  |

Final schema status: **Draft - not yet frozen for pilot testing**
