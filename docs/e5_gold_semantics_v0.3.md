# E5 gold semantics v0.3

Status: policy and batch-1 case content approved by Chloe Ruoyu Xu on
2026-07-29. The pinned private gold replay completed 4/4 clean locally.

This public document records policy only. Exact batch cases, gold actions,
response contracts, snapshots, expected hashes, and evaluator output remain
under `evaluator_data/local_review_decisions/` and are excluded from Git.

## Public synthetic fixture boundary

`verticals/retail/cases/RETAIL-E5-001.json` is a `synthetic_fixture` backed by
the repository's synthetic retail data. It exists only for public contract
tests, wrapper evidence, and demos. It is never selected for formal E5
conversion or replay.

Formal E5 conversion reads only the gitignored owner-reviewed
`evaluator_data/local_review_decisions/E5_cases_batch1.json` and the pinned
upstream snapshot referenced by those private records.

## Verdict

An E5 case passes only when all of the following hold:

1. every `response_contract.required_info` item appears in user-facing
   assistant turns;
2. no `response_contract.forbidden_info` item appears;
3. the predicted and gold retail states have identical agent-DB and user-DB
   hashes;
4. no failure class is detected.

There is no partial credit at case level. Harness failures produce `error`;
agent-caused failures produce `fail`.

## Final-state comparison

Both sides are deterministic replays into fresh environments:

- replay `gold_write_actions` to build the gold state;
- replay successful predicted tool calls to build the predicted state;
- compare the environment's agent-DB and user-DB hashes;
- cover all retail `orders`, `users`, and `products`, with no excluded paths.

A gold action that cannot be replayed cleanly invalidates the case. Real
conversion must record the pinned snapshot reference/hash, expected hashes, and
`gold_replay_clean=true` locally before scoring.

The formal verdict remains ours. Each final experiment run also records the
upstream DB-only component under `run_log.sanity.tau3_db`. That sanity result
never overrides the verdict; a Criterion-B disagreement is reproduced by
Jessica and adjudicated by Chloe.

## Protocol v1.6 public output boundary

Chloe approved the protocol v1.6 public E5 output rule on 2026-08-13. The
agent-reported `final_state` contains only tool-observable action evidence:
`action_taken`, plus `escalation_reason` when the action is `escalate`.
Unavailable `ticket_id`, `order_status`, and other business-state values are
neither required nor permitted in the public response.

This public shape does not replace the v0.3 verdict. Authoritative final-state
comparison continues to replay successful observed tool calls and approved
gold actions locally. A normally completed, schema-valid run whose evaluator
verdict is `fail` is a frozen model result, not an infrastructure error, and is
not retry-eligible for score improvement.

## Tool policy

Every case exposes the complete 16-tool retail registry:

- seven read tools;
- seven write tools;
- `calculate`;
- `transfer_to_human_agents`.

Read calls are not order- or count-scored. Writes are judged by final state.
`transfer_to_human_agents` is generic and non-mutating, but may be required as
a terminal action.

Upstream `Action.compare_with_tool_call` has been verified. When
`compare_args` is `null`, all tool-call arguments are compared. When it is an
empty list, only the tool name must match; no arguments are compared.

## Failures

All detected failures are recorded. `primary_failure` uses this precedence:

1. `tool_runtime_failure`
2. `disallowed_tool`
3. `invalid_arguments`
4. `duplicate_side_effect`
5. `incorrect_mutation`
6. `missing_required_action`

`disallowed_tool`, `invalid_arguments`, and `duplicate_side_effect` are hard
failures even when the final DB matches gold. A missing terminal handoff is
also a hard failure because it cannot be detected from state hashes.

## Response matching

Matching uses user-facing assistant turns only:

- `substring`: normalized text matching;
- `number`: numeric extraction with declared tolerance;
- `any_of`: any declared alternative may match;
- `regex`: permitted only with a documented reason.

An empty `required_info` requires an explicit waiver. `forbidden_info` must
describe information or claims that cannot appear in a correct response.

## Rerun and adjudication

A harness error is rerun exactly once. If it errors again, report it as
`error` and show the error count beside pass rate. If more than 5 percent of a
framework's final case attempts are errors, the whole framework sweep is
invalid and must be rerun.

Chloe adjudicates Criterion-B disagreements after Jessica reproduces them.
Gold-changing resolutions require renewed approval and reruns for every
framework.

The repository provides the retry, sweep-summary, and `tau3_db` recording
policy in `adapter/e5_run_policy.py`. The final experiment runner must still
supply the native DB result and use the frozen model, simulator, and seed for
all three frameworks.
