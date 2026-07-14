import argparse
import json
import operator
import os
import sys
import time
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.schemas import AgentRunResult, BenchmarkTask

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "langgraph"

load_dotenv(ROOT / ".env", override=True)


class MessagesState(TypedDict):
    messages: Annotated[list, operator.add]


def _run_agent(prompt: str) -> str:
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )

    def call_model(state: MessagesState):
        response = llm.invoke(
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
    graph_builder.add_edge("call_model", END)

    agent_graph = graph_builder.compile()

    result = agent_graph.invoke({"messages": [HumanMessage(content=prompt)]})
    return result["messages"][-1].content


def run_task(task: BenchmarkTask) -> AgentRunResult:
    start = time.perf_counter()
    try:
        final_output = _run_agent(task.prompt)
        return AgentRunResult(
            task_id=task.task_id,
            framework=FRAMEWORK_NAME,
            vertical=task.vertical,
            final_output=final_output,
            latency_seconds=time.perf_counter() - start,
            success=True,
        )
    except Exception as exc:
        return AgentRunResult(
            task_id=task.task_id,
            framework=FRAMEWORK_NAME,
            vertical=task.vertical,
            final_output="",
            latency_seconds=time.perf_counter() - start,
            success=False,
            error=f"{type(exc).__name__}: {exc}",
        )


def _load_task(task_path: Path) -> BenchmarkTask:
    with open(task_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BenchmarkTask(
        task_id=data["task_id"],
        vertical=data["vertical"],
        prompt=data["prompt"],
        expected_output_type=data.get("expected_output_type", "json"),
        metadata=data.get("metadata", {}),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, default=TASK_PATH)
    args = parser.parse_args()

    task = _load_task(args.task)
    result = run_task(task)
    append_result(result)

    print(f"\n=== {FRAMEWORK_NAME} Result ===")
    print(f"success={result.success} latency={result.latency_seconds:.2f}s")
    print(result.final_output or result.error)


if __name__ == "__main__":
    main()
