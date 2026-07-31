"""LangGraph thin wrapper for the WS3 retail vertical (tau-retail / E5)."""

from __future__ import annotations

import json
import operator
import os
import sys
import uuid
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.e5_session import run_e5_session
from adapter.tau_retail_env import make_retail_env
from adapter.runtime import (
    GenerationSettings,
    GenerationSettingsResolution,
    begin_run,
    configured_generation_settings,
    failed_model_construction_settings,
    finish_run,
    resolve_generation_settings,
    start_run_timing,
)
from adapter.schemas import AgentRunResult, BenchmarkTask
from frameworks.langgraph_agent.retail_tools import make_retail_tools

DATA_DIR = str(ROOT / "verticals" / "retail")
FRAMEWORK_NAME = "langgraph"
WRAPPER_VERSION = "0.1.0"

load_dotenv(ROOT / ".env", override=False)


class MessagesState(TypedDict):
    messages: Annotated[list, operator.add]


def _system_prompt() -> str:
    return (
        "You are a retail customer-support agent. Use the provided tools to resolve "
        "the customer's issue. Follow policy and only use allowed tools. "
        "When finished, reply with a single JSON object (no markdown) containing "
        'at least "resolution" (string) and "actions_taken" (array of strings).'
    )


def _build_llm(
    generation_settings: GenerationSettings,
) -> tuple[ChatOpenAI, GenerationSettingsResolution]:
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=generation_settings.temperature,
        max_tokens=generation_settings.max_output_tokens,
        seed=generation_settings.seed,
    )
    effective_settings = GenerationSettings(
        temperature=llm.temperature,
        max_output_tokens=llm.max_tokens,
        seed=llm.seed,
    )
    return llm, resolve_generation_settings(
        generation_settings,
        effective_settings,
    )


def _run_retail_agent(
    llm: ChatOpenAI,
    env: RetailEnv,
    prompt: str,
    allowed_tools: list[str] | None,
) -> tuple[str, dict[str, int | None], list[dict[str, Any]], dict[str, Any]]:
    tools = make_retail_tools(env, allowed_tools)
    use_tools = bool(tools)
    llm_bound = llm.bind_tools(tools) if use_tools else llm

    def call_model(state: MessagesState):
        response = llm_bound.invoke(
            [SystemMessage(content=_system_prompt())] + state["messages"]
        )
        return {"messages": [response]}

    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("call_model", call_model)
    graph_builder.add_edge(START, "call_model")

    if use_tools:
        graph_builder.add_node("tools", ToolNode(tools))
        graph_builder.add_conditional_edges("call_model", tools_condition)
        graph_builder.add_edge("tools", "call_model")
    else:
        graph_builder.add_edge("call_model", END)

    agent_graph = graph_builder.compile()
    result = agent_graph.invoke({"messages": [HumanMessage(content=prompt)]})

    usage_rows = [
        message.usage_metadata
        for message in result["messages"]
        if getattr(message, "usage_metadata", None)
    ]
    token_usage = {
        key: sum(int(row.get(key, 0) or 0) for row in usage_rows) if usage_rows else None
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    final_output = str(result["messages"][-1].content)
    return final_output, token_usage, env.get_trace(), env.get_final_state()


def run_retail_task(task: BenchmarkTask, *, seed: int | None = None) -> AgentRunResult:
    """Run one retail benchmark case through LangGraph + RetailEnv."""
    if not task.case_id:
        raise ValueError("retail tasks require case_id")

    requested_settings = configured_generation_settings()
    if seed is not None:
        requested_settings = GenerationSettings(
            temperature=requested_settings.temperature,
            max_output_tokens=requested_settings.max_output_tokens,
            seed=seed,
        )

    timing = start_run_timing()
    try:
        llm, settings_resolution = _build_llm(requested_settings)
        model_error = None
    except Exception as exc:
        llm = None
        model_error = exc
        settings_resolution = failed_model_construction_settings(requested_settings)

    context = begin_run(
        FRAMEWORK_NAME,
        "langgraph",
        settings_resolution,
        timing,
        model_construction_failed=model_error is not None,
    )
    if model_error is not None:
        result = finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=f"{type(model_error).__name__}: {model_error}",
        )
        result.raw_metadata["wrapper_version"] = WRAPPER_VERSION
        return result

    run_seed = context.seed
    environment_seed = run_seed if run_seed is not None else 42
    env = make_retail_env(task, data_dir=DATA_DIR, seed=environment_seed)

    try:
        env.reset(
            task.case_id,
            reset_id=f"run-{uuid.uuid4().hex}",
            seed=environment_seed,
        )
        session = None
        if task.task_id == "E5":
            def run_turn(prompt: str):
                output, usage, _, _ = _run_retail_agent(
                    llm,
                    env,
                    prompt,
                    task.allowed_tools,
                )
                return output, usage

            session = run_e5_session(task, run_turn)
            final_output = session.final_output
            token_usage = session.token_usage
            tool_trace = env.get_trace()
            final_state = env.get_final_state()
        else:
            final_output, token_usage, tool_trace, final_state = _run_retail_agent(
                llm,
                env,
                task.prompt,
                task.allowed_tools,
            )
        result = finish_run(
            context,
            task,
            final_output=final_output,
            success=True,
            raw_tool_logs=tool_trace,
            token_usage=token_usage,
        )
        result.raw_metadata.update(
            {
                "wrapper_version": WRAPPER_VERSION,
                "final_state": final_state,
            }
        )
        if session is not None:
            result.raw_metadata.update(
                {
                    "assistant_turns": session.assistant_turns,
                    "user_simulator": session.simulator,
                }
            )
        return result
    except Exception as exc:
        tool_trace = env.get_trace() if env.case_id else []
        result = finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            raw_tool_logs=tool_trace,
        )
        result.raw_metadata["wrapper_version"] = WRAPPER_VERSION
        if env.case_id:
            result.raw_metadata["final_state"] = env.get_final_state()
        return result


def build_wrapper_evidence() -> dict[str, Any]:
    from frameworks.langgraph_agent.retail_evidence import build_wrapper_evidence as _build

    return _build()


def main() -> None:
    import argparse

    from adapter.task_loader import load_task

    parser = argparse.ArgumentParser(
        description="Run a retail case via LangGraph + RetailEnv."
    )
    parser.add_argument(
        "--task",
        type=Path,
        default=ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json",
    )
    parser.add_argument(
        "--write-evidence",
        type=Path,
        default=None,
        help="Write offline wrapper-evidence JSON and exit (no LLM).",
    )
    args = parser.parse_args()

    if args.write_evidence:
        evidence = build_wrapper_evidence()
        args.write_evidence.parent.mkdir(parents=True, exist_ok=True)
        args.write_evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(f"wrote wrapper evidence to {args.write_evidence}")
        return

    task = load_task(args.task)
    result = run_retail_task(task)
    append_result(result)

    print(f"\n=== {FRAMEWORK_NAME} retail Result ===")
    print(f"success={result.success} latency={result.latency_seconds:.2f}s")
    print(result.final_output or result.error)


if __name__ == "__main__":
    main()
