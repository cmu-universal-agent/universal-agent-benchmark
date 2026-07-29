# E5 gold semantics v0.2

Status: approved by Chloe Ruoyu Xu on 2026-07-29.

This public document records policy only. Exact batch cases, gold actions,
response contracts, snapshots, expected hashes, and evaluator output remain
under `evaluator_data/local_review_decisions/` and are excluded from Git.

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

## Tool policy

Every case exposes the complete 16-tool retail registry:

- seven read tools;
- seven write tools;
- `calculate`;
- `transfer_to_human_agents`.

Read calls are not order- or count-scored. Writes are judged by final state.
`transfer_to_human_agents` is generic and non-mutating, but may be required as
a terminal action.

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

A harness error is rerun once. If it errors again, report it as `error` and
show the error count beside pass rate. Chloe adjudicates Criterion-B
disagreements after Jessica reproduces them. Gold-changing resolutions require
renewed approval and reruns for every framework.
