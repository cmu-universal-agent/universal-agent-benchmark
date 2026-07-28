# Framework Field Availability

Generated from the recorded JSONL rows. `unknown` model rows are legacy development results and must not be used for model-controlled comparisons.

| Framework | Model | Rows | run_id | experiment_id | framework_version | model_provider | model_name | temperature | prompt_version | started_at | completed_at | raw_output | tool_calls | token_usage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crewai | gpt-4o-mini | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 3/4 | 4/4 | 4/4 |
| langgraph | gpt-4o-mini | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 3/4 | 4/4 | 4/4 |
| openai_agents_sdk | gpt-4o-mini | 7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 6/7 | 7/7 | 7/7 |

## Interpretation

- `n/n`: field is recorded for every row in the group.
- `0/n`: field is missing or null for every row.
- A partial count means the adapter or result format changed between runs.
- Empty `tool_calls` is valid for a no-tool run.
- A present `token_usage` object may still contain null counts when the provider does not expose usage through the framework adapter.
