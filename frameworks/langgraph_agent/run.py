import argparse
import operator
import os
import sys
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.runtime import (
    GenerationSettings,
    GenerationSettingsResolution,
    configured_generation_settings,
    resolve_generation_settings,
    run_framework_task,
)
from adapter.schemas import AgentRunResult, BenchmarkTask
from adapter.task_loader import load_task
from adapter.vertical_routing import select_vertical_tools
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "langgraph"
RECURSION_LIMIT = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "25"))

load_dotenv(ROOT / ".env", override=False)


class MessagesState(TypedDict):
    messages: Annotated[list, operator.add]


@tool
def search_literature(pubmed_id: str) -> str:
    """Look up the research abstract for a given PubMed ID."""
    return medical_tools.search_literature(pubmed_id)


@tool
def get_review_history(parent_asin: str) -> str:
    """Look up the yearly review-count and average-rating history for a product."""
    return ecommerce_tools.get_review_history(parent_asin)


TOOLS_BY_VERTICAL = {
    "medical_diagnostic": {"search_literature": search_literature},
    "ecommerce_trend_research": {"get_review_history": get_review_history},
}


def _select_tools(vertical: str, allowed_tools: list[str] | None) -> list:
    return select_vertical_tools(TOOLS_BY_VERTICAL, vertical, allowed_tools)


def _extract_token_usage(messages: list[Any]) -> dict[str, int | None]:
    rows = [
        row
        for message in messages
        if isinstance(row := getattr(message, "usage_metadata", None), dict)
    ]
    usage: dict[str, int | None] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        values = [
            value
            for row in rows
            if isinstance((value := row.get(key)), int)
            and not isinstance(value, bool)
            and value >= 0
        ]
        usage[key] = sum(values) if values else None
    if (
        usage["total_tokens"] is None
        and usage["input_tokens"] is not None
        and usage["output_tokens"] is not None
    ):
        usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    return usage


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


def _run_agent(
    prompt: str,
    vertical: str,
    allowed_tools: list[str] | None = None,
    generation_settings: GenerationSettings | None = None,
    llm: ChatOpenAI | None = None,
) -> tuple[str, dict[str, int | None]]:
    if llm is None:
        requested = generation_settings or configured_generation_settings()
        llm, _ = _build_llm(requested)

    tools = _select_tools(vertical, allowed_tools)
    use_tools = bool(tools)
    llm_bound = llm.bind_tools(tools) if use_tools else llm

    def call_model(state: MessagesState):
        response = llm_bound.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a benchmark smoke-test agent. "
                        "Follow the user's output format exactly. "
                        "Do not add markdown."
                    )
                )
            ]
            + state["messages"]
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

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content=prompt)]},
        config={"recursion_limit": RECURSION_LIMIT},
    )
    token_usage = _extract_token_usage(result["messages"])
    return str(result["messages"][-1].content), token_usage


def run_task(task: BenchmarkTask) -> AgentRunResult:
    if task.vertical == "retail":
        from frameworks.langgraph_agent.retail_run import run_retail_task

        return run_retail_task(task)

    return run_framework_task(
        task,
        framework=FRAMEWORK_NAME,
        package_name="langgraph",
        tool_modules=[medical_tools, ecommerce_tools],
        requested_settings=configured_generation_settings(),
        build_model=_build_llm,
        run_model=lambda llm, requested_settings: _run_agent(
            task.prompt, task.vertical, task.allowed_tools, requested_settings, llm
        ),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, default=TASK_PATH)
    args = parser.parse_args()

    task = load_task(args.task)
    result = run_task(task)
    append_result(result)

    print(f"\n=== {FRAMEWORK_NAME} Result ===")
    print(f"success={result.success} latency={result.latency_seconds:.2f}s")
    print(result.final_output or result.error)


if __name__ == "__main__":
    main()
