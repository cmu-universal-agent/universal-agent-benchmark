import argparse
import operator
import os
import sys
from pathlib import Path
from typing import Annotated

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
from adapter.runtime import begin_run, finish_run
from adapter.schemas import AgentRunResult, BenchmarkTask
from adapter.task_loader import load_task
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "langgraph"

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
    available = TOOLS_BY_VERTICAL.get(vertical, {})
    if allowed_tools is None:
        return list(available.values())
    allowed = set(allowed_tools)
    return [tool_value for name, tool_value in available.items() if name in allowed]


def _run_agent(
    prompt: str, vertical: str, allowed_tools: list[str] | None = None
) -> tuple[str, dict[str, int | None]]:
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )

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
    return str(result["messages"][-1].content), token_usage


def run_task(task: BenchmarkTask) -> AgentRunResult:
    context = begin_run(FRAMEWORK_NAME, "langgraph")
    medical_tools.reset_call_log()
    ecommerce_tools.reset_call_log()
    try:
        final_output, token_usage = _run_agent(
            task.prompt, task.vertical, task.allowed_tools
        )
        return finish_run(
            context,
            task,
            final_output=final_output,
            success=True,
            raw_tool_logs=[*medical_tools.call_log, *ecommerce_tools.call_log],
            token_usage=token_usage,
        )
    except Exception as exc:
        return finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            raw_tool_logs=[*medical_tools.call_log, *ecommerce_tools.call_log],
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
