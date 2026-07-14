# Framework Suitability Matrix

Generated: 2026-07-14 20:25 UTC

**Note:** results below reflect the latest recorded run per (task, framework) in `results/metrics/*.jsonl`, which may not match the model currently configured in `.env` (currently `gpt-5.4-mini`) -- results aren't tagged with which model produced them, and this session tested gpt-4o-mini, gpt-5-nano, and gpt-5.4-mini. Re-run `scripts/run_benchmark.py` and regenerate this report for numbers matching the current model.

## Smoke Test

| Framework | n | Tool Overuse | Avg Latency | Failure Modes |
|---|---|---|---|---|
| openai_agents_sdk | 1 | 0/1 | 2.7s | ok=1 |
| langgraph | 1 | 0/1 | 3.3s | ok=1 |
| crewai | 1 | 0/1 | 9.8s | ok=1 |

**Avg latency (s):**
```
openai_agents_sdk    #####---------------   2.7s
langgraph            #######-------------   3.3s
crewai               ####################   9.8s
```

## Medical Diagnostic Assistant

| Framework | n | Accuracy | Confidently Wrong | Medical Safety OK | Tool Overuse | Avg Latency | Failure Modes |
|---|---|---|---|---|---|---|---|
| openai_agents_sdk | 10 | 80% (8/10) | 1/10 | 8/10 | 0/10 | 3.6s | ok=10 |
| langgraph | 10 | 80% (8/10) | 2/10 | 8/10 | 0/10 | 3.9s | ok=10 |
| crewai | 10 | 70% (7/10) | 1/10 | 9/10 | 0/10 | 4.0s | ok=10 |

**Accuracy:**
```
openai_agents_sdk    ################----  80.0%
langgraph            ################----  80.0%
crewai               ##############------  70.0%
```

**Avg latency (s):**
```
openai_agents_sdk    ##################--   3.6s
langgraph            ###################-   3.9s
crewai               ####################   4.0s
```

## E-commerce Trend Researcher

| Framework | n | Accuracy | Confidently Wrong | Tool Overuse | Avg Latency | Failure Modes |
|---|---|---|---|---|---|---|
| openai_agents_sdk | 10 | 70% (7/10) | 1/10 | 0/10 | 4.4s | ok=10 |
| langgraph | 10 | 70% (7/10) | 1/10 | 0/10 | 5.5s | ok=10 |
| crewai | 10 | 70% (7/10) | 1/10 | 0/10 | 5.7s | ok=10 |

**Accuracy:**
```
openai_agents_sdk    ##############------  70.0%
langgraph            ##############------  70.0%
crewai               ##############------  70.0%
```

**Avg latency (s):**
```
openai_agents_sdk    ###############-----   4.4s
langgraph            ###################-   5.5s
crewai               ####################   5.7s
```

## Qualitative Findings (this session)

These come from targeted tests run during development, not just the raw metrics above:

- **Tool-failure resilience differs by framework.** When the mock tool raises an exception, `openai_agents_sdk` and `crewai` catch it internally and let the model recover with a graceful best-effort answer. `langgraph`'s default `ToolNode` only catches malformed tool-call errors, not arbitrary exceptions raised inside tool execution -- the task fails outright instead of degrading gracefully, unless `handle_tool_errors` is explicitly configured.
- **Tool overuse is model-dependent, not a fixed framework trait.** Under `gpt-4o-mini`, `crewai` calls the (unneeded) literature-lookup tool on the large majority of medical tasks despite being told not to -- 11/15 and, in a later re-run, 9/10, so it's consistent under this model, not a one-off. The same tool-overuse tendency vanished entirely under both `gpt-5-nano` and `gpt-5.4-mini` (0/15, 0/15).
- **Schema drift found and fixed.** `crewai` was intermittently nesting the entire answer under an `"answer"` wrapper key on e-commerce tasks instead of the flat schema the prompt asked for. Root cause: `frameworks/crewai_agent/run.py`'s `Task.expected_output` was hardcoded to the smoke-test schema (`task_id, answer, safety_note`) for every vertical, directly contradicting the richer schema specified in the medical/e-commerce prompts -- CrewAI was being given two conflicting format instructions. Fixed by making `expected_output` generic ("matches the schema specified in the task description above"); a fresh full re-run afterward came back 10/10 clean, flat-schema output.
- **Escalation instruction is dropped by all three frameworks.** When the model answers "maybe" on a medical task, the prompt explicitly asks it to recommend a qualified medical professional review the primary literature. All three frameworks correctly reason about uncertainty ("not statistically significant") but skip this specific referral language.
- **`gpt-4o-mini` has a near-universal `"safety_note"` -> `"safe_note"` typo on medical tasks.** In the latest full sweep, `langgraph` and `crewai` misspelled the key on 10/10 medical tasks, `openai_agents_sdk` on 8/10 -- despite the prompt spelling out `safety_note` exactly. The model's actual reasoning and uncertainty handling is fine; this is a narrow but near-total literal-key-compliance failure specific to this model, and it silently defeats the exact-disclaimer safety check unless something normalizes or fuzzy-matches the key.
- **Model choice affects latency far more than accuracy.** `gpt-4o-mini` averaged ~3-5s/call; `gpt-5-nano` and `gpt-5.4-mini` averaged 8-24s/call (occasional 100s+ outliers) for similar or modestly better accuracy on the harder e-commerce trend task.

## Recommendation

- **Medical Diagnostic Assistant** (low tolerance for hallucination, structured reasoning, safe refusal): reasoning quality (accuracy, uncertainty handling) is solid across all three frameworks, but literal safety-disclaimer compliance is currently poor under `gpt-4o-mini` specifically (see the `safe_note` typo finding above) -- this vertical should not be called safety-compliant as configured today, independent of framework choice. `openai_agents_sdk` and `crewai` are the safer picks on tool discipline under a failing tool (graceful degradation); `crewai`'s tool-overuse under `gpt-4o-mini` is a second, separate risk to weigh if that model stays in use. All three need explicit prompting/validation work on both the escalation-language and exact-key requirements before this vertical could be called safety-compliant.
- **E-commerce Trend Researcher** (creative reasoning, frequent tool use, flexible synthesis): accuracy is the binding constraint here (40-80% depending on model), not framework choice -- all three show the same trend-direction reasoning weaknesses (a recency bias toward "declining" regardless of the actual multi-year pattern). Schema compliance is no longer a differentiator now that the `crewai` expected_output conflict is fixed -- all three produced clean flat JSON in the latest sweep.
