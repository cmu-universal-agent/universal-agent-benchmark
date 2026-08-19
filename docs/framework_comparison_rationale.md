# Framework Comparison Rationale

Last updated: July 15, 2026

## Purpose

This document explains why Workstream #2 compares LangGraph, CrewAI, and the
OpenAI Agents SDK, which framework-level capabilities the benchmark should
measure, and how those capabilities map to the eight core healthcare and
e-commerce tasks.

The document defines hypotheses and evaluation dimensions. It does not claim
that one framework is already better than another. Framework suitability must
be determined from controlled benchmark results.

## Working Definition of an Agent Framework

For this project, an agent framework covers two related layers:

1. **Single-agent runtime:** how a model receives instructions, invokes tools,
   manages context or memory, validates outputs, and continues its reasoning
   loop until a task is complete.
2. **Workflow and multi-agent coordination:** how multiple agents or execution
   steps share state, route work, transfer control, pause for human approval,
   recover from failure, and expose traces for evaluation.

The underlying model is not treated as part of the framework comparison. The
controlled baseline fixes the model and other experimental conditions so that
observed differences can be attributed as far as possible to orchestration and
runtime behavior.

## Why These Three Frameworks

### LangGraph

LangGraph is a low-level orchestration runtime for long-running, stateful
agents. Its graph model makes state, nodes, edges, conditional routing, and
execution paths explicit. Its documented strengths include durable execution,
persistence, human-in-the-loop control, and state inspection.

These characteristics make LangGraph relevant to workflows that require
explicit control, recoverability, or auditability. In this benchmark, those
properties are hypotheses to test, especially in healthcare safety and retail
policy tasks.

Official references:

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)

### CrewAI

CrewAI provides two complementary abstractions. Crews organize autonomous
agents around roles, goals, tools, and collaborative tasks. Flows provide
event-driven execution, conditional routing, state management, and more
explicit control. A benchmark implementation must state whether it uses a
Crew, a Flow, or a combination of both.

These characteristics make CrewAI relevant to exploratory research,
role-specialized collaboration, and hybrid workflows that combine autonomous
subtasks with controlled execution. The benchmark must test this behavior
rather than assume that role-based collaboration improves performance.

Official reference:

- [CrewAI documentation](https://docs.crewai.com/)

### OpenAI Agents SDK

The OpenAI Agents SDK provides a Python-first agent loop with function tools,
structured output support, guardrails, sessions, agents-as-tools, handoffs,
human-in-the-loop mechanisms, MCP integration, and built-in tracing. Handoffs
transfer control to a specialist agent, while agents-as-tools support a
manager-style pattern in which one agent retains control.

These characteristics make the SDK relevant to lightweight single-agent
runtimes and explicit specialist delegation. Its current feature set should
not be reduced to a thin model wrapper; the benchmark should measure which of
its runtime controls are actually available through the shared adapter.

Official references:

- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- [Tracing](https://openai.github.io/openai-agents-python/tracing/)

## Frameworks Considered but Out of Scope

Microsoft Agent Framework and Google Agent Development Kit are useful related
frameworks for the literature and framework-selection discussion. They are not
part of the first controlled experiment because adding more implementations
would increase development and validation work without increasing the number
of core benchmark cases.

The current comparison therefore remains:

```text
LangGraph vs. CrewAI vs. OpenAI Agents SDK
```

## Vertical-Aware Adapter Contract

The benchmark compares framework behavior without pretending that healthcare
and e-commerce require identical tools. Every case first passes through the
shared adapter layer:

1. `adapter.task_loader` validates the agent-visible case and resolves its
   runtime vertical.
2. `adapter.vertical_routing` applies the same vertical and tool allow-list
   rules for all three frameworks.
3. Each framework's single `run.py` entry point registers its native wrapper
   for the selected tools. E5 alone enters the stateful retail runtime; the
   other seven tasks use their healthcare or e-commerce content path.
4. `adapter.runtime` normalizes every execution to `AgentRunResult`; evaluators
   run afterward and never expose gold or expected state to the agent.

This is a vertical-aware adapter, not a different benchmark per framework:
the case, model configuration, output contract, and evaluation rule remain
fixed while only framework-native orchestration changes. Formal E5 uses the
pinned private `TauRetailEnv`; public synthetic validation uses `RetailEnv`
through the same environment interface.

## Comparison Dimensions

| Dimension | What Is Being Compared | Example Measurements |
|---|---|---|
| Agent loop completion | Whether the runtime can continue through model and tool steps to a valid final answer | completion rate, timeout rate, maximum-turn failures |
| Tool control | Tool selection, argument generation, allow-list enforcement, and result handling | tool success rate, disallowed calls, argument errors, tool overuse |
| State consistency | Whether important information and environment state remain correct across steps | missing state, stale state, incorrect final state |
| Guardrails and validation | Whether unsafe, disallowed, or malformed inputs and outputs are detected | unsafe response rate, rejection accuracy, raw and repaired schema validity |
| Failure recovery | Behavior after a tool error, timeout, malformed result, or interrupted run | recovery rate, retry count, terminal error stage |
| Orchestration and routing | Whether tasks are delegated to the correct step or specialist | routing accuracy, unnecessary handoffs, incomplete delegation |
| Human-in-the-loop | Whether risky actions can pause, expose sufficient context, and resume correctly | approval routing, resume success, state preservation |
| Observability | Whether the adapter can capture comparable execution evidence | trace completeness, tool-call detail, timestamps, structured errors |
| Runtime overhead | Additional resources introduced by the framework implementation | latency, model calls, tokens, estimated cost |
| Developer effort | Effort needed to build and maintain an equivalent task workflow | implementation size, configuration complexity, debugging effort |

Developer effort is a qualitative suitability factor and must not be mixed
into the task-success score.

## Architecture-to-Metric Mapping

| Framework characteristic | Benchmark question | Required evidence |
|---|---|---|
| Explicit graph or workflow | Does explicit routing reduce instruction drift or improve recovery? | node/step sequence, state transitions, terminal stage |
| Role-based collaboration | Do specialist roles improve synthesis without adding excessive calls or ambiguity? | agent sequence, delegations, model-call count, output quality |
| Handoffs or agents-as-tools | Is the correct specialist selected, and is relevant context preserved? | source and destination agent, handoff input, final agent, context checks |
| Persistent state or sessions | Can a task resume without losing or duplicating information? | checkpoint/session ID, pre/post state, resume status |
| Guardrails | Are unsafe or invalid actions blocked at the correct stage? | guardrail type, trigger stage, blocked action, final status |
| Built-in tracing or hooks | Can the shared Run Log be completed without inventing unavailable data? | native trace fields and adapter-normalized fields |

## Mapping to the Eight Core Tasks

| Task | Primary framework pressures | Core measurements |
|---|---|---|
| H1: Evidence-Based Medical QA | evidence handling, structured output, uncertainty | decision accuracy, evidence validity, schema validity, unsupported claims |
| H2: Symptom Triage Safety | safety guardrails, escalation, missing information | unsafe advice rate, escalation accuracy, refusal or clarification quality |
| H4: Clinical Note Summarization | long context, state retention, factual consistency | required-field coverage, omissions, contradictions, latency |
| H5: Refusal and Boundary Handling | policy enforcement, guardrails, adversarial instructions | appropriate refusal, prohibited content, safe next step |
| E1: Product Trend Research | exploratory synthesis, source coverage, tool restraint | source validity, insight quality, hallucination, tool overuse |
| E2: Product Recommendation | constraint tracking, catalog state, explanation | constraint satisfaction, product validity, recommendation relevance |
| E3: Return/Refund Policy Decision | rule application, conditional routing, final state | decision accuracy, policy evidence, disallowed action, state correctness |
| E5: Customer Support Tool Use | multi-step tools, error recovery, customer response | tool sequence, argument validity, recovery rate, latency, final answer |

## Stress-Test Mapping

The shared stress types should isolate one controlled change whenever possible.

| Stress type | Framework capability under test |
|---|---|
| `standard` | baseline completion and output validity |
| `ambiguous_input` | clarification, uncertainty, and routing behavior |
| `missing_information` | safe stopping and required-information checks |
| `conflicting_evidence` | evidence reconciliation and state consistency |
| `tool_failure` | error propagation, retry, fallback, and recovery |
| `long_context` | context retention, state management, and latency |
| `policy_or_safety_trap` | guardrails, refusal, and prohibited-action prevention |
| `repeated_run` | behavioral consistency and output variance |

## Experimental Design

### Tier 1: Controlled Single-Agent Baseline

The primary comparison should use one functionally equivalent single-agent
workflow per framework. All frameworks receive the same task, model, prompt,
tools, tool schemas, output schema, generation settings, budgets, timeouts,
retry limits, and evaluator.

This tier isolates the shared agent loop, tool handling, validation, logging,
and error behavior. It should be completed before adding multi-agent designs.

### Tier 2: Equivalent Orchestration Scenario

A smaller subset may test an equivalent multi-step structure:

```text
Router or triage step
    -> domain specialist
    -> safety or policy reviewer
    -> final response
```

Each implementation must have the same functional roles and access to the
same information. Framework-native orchestration may differ, but the intended
work performed by each step must remain comparable.

### Tier 3: Framework-Native Best Practice

An optional final experiment may allow each framework to use its native
strengths. These results must be reported separately from the controlled
baseline because architecture, prompts, and execution budgets may no longer
be equivalent.

## Control Variables

For the controlled baseline, keep the following fixed:

- model provider, model name, and model version;
- generation settings;
- prompt content and prompt version;
- benchmark cases and case ordering;
- tool implementations, schemas, and backing data;
- allowed-tool lists;
- output schemas and evaluators;
- maximum turns, tool calls, retries, timeout, and token budget;
- repeat count and randomization procedure;
- hardware and network assumptions where measurable.

Model-sensitivity experiments must be labeled separately. Results from
different models must never be combined into one framework ranking.

## Required Run-Log Evidence

The shared Run Log should support the comparison dimensions above. At minimum,
each run should record:

- run, experiment, case, task, and repeat identifiers;
- framework and framework version;
- model provider, model name, and generation settings;
- start/end timestamps, status, latency, and timeout information;
- raw output and parsed output;
- raw schema validity, repair requirement, and repaired validity;
- ordered tool calls with arguments, allow-list decision, result or error, and latency;
- agent, node, step, or handoff sequence when available;
- token usage and estimated cost when available;
- structured error stage and failure classification;
- evaluator results and rubric version.

If a framework does not expose a field, record it as unavailable rather than
inferring or fabricating a value. Field availability is itself part of the
observability comparison.

## Hypotheses to Test

The following statements are hypotheses, not conclusions:

1. Explicit state and routing may improve recoverability and auditability in
   healthcare and policy-constrained tasks.
2. Role-specialized collaboration may improve exploratory retail synthesis,
   but may add model calls, latency, and attribution difficulty.
3. Lightweight handoff or manager patterns may reduce implementation overhead,
   but performance depends on context transfer and guardrail placement.
4. Framework differences may become more visible under tool failure, long
   context, safety traps, and repeated runs than on standard question-answering
   cases.
5. Model capability may interact with framework behavior; this interaction
   must be tested separately from the fixed-model framework comparison.

## Interpretation Rules

- Do not treat framework documentation claims as benchmark findings.
- Do not rank frameworks using runs produced by different models.
- Do not interpret mock dashboard data as experimental evidence.
- Do not award higher scores merely because a framework makes more tool or
  agent calls.
- Separate task quality, safety, reliability, efficiency, observability, and
  developer effort instead of collapsing them prematurely into one score.
- Report missing native telemetry explicitly.
- Distinguish model errors, framework-runtime behavior, adapter bugs, task
  design problems, and evaluator errors during failure analysis.

## Decision for Workstream #2

The first formal implementation remains focused on LangGraph, CrewAI, and the
OpenAI Agents SDK across the eight approved core tasks. The immediate goal is
not to prove that one framework is universally superior. It is to identify the
conditions under which each implementation remains reliable, becomes costly,
loses control, or fails to provide sufficient evidence for audit and recovery.
