import json
import operator
import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict


ROOT = Path(__file__).resolve().parents[2]
TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"

load_dotenv(ROOT / ".env", override=True)


class MessagesState(TypedDict):
    messages: Annotated[list, operator.add]


def main():
    with open(TASK_PATH, "r", encoding="utf-8") as f:
        task = json.load(f)

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

    result = agent_graph.invoke(
        {"messages": [HumanMessage(content=task["prompt"])]}
    )

    print("\n=== LangGraph Result ===")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
