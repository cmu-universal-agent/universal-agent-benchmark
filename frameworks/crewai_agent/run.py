import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.schemas import AgentRunResult, BenchmarkTask
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "crewai"

load_dotenv(ROOT / ".env", override=True)


@tool("search_literature")
def search_literature(pubmed_id: str) -> str:
    """Look up the research abstract for a given PubMed ID."""
    return medical_tools.search_literature(pubmed_id)


@tool("get_review_history")
def get_review_history(parent_asin: str) -> str:
    """Look up the yearly review-count and average-rating history for a product."""
    return ecommerce_tools.get_review_history(parent_asin)


TOOLS_BY_VERTICAL = {
    "medical_diagnostic": [search_literature],
    "ecommerce_trend_research": [get_review_history],
}


def _run_agent(prompt: str, vertical: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")

    # CrewAI often expects OpenAI models in this form:
    # openai/gpt-4, openai/gpt-4o-mini, etc.
    crewai_model_name = model_name if "/" in model_name else f"openai/{model_name}"

    llm = LLM(
        model=crewai_model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )

    tools = TOOLS_BY_VERTICAL.get(vertical, [])

    agent = Agent(
        role="Benchmark Smoke Test Agent",
        goal="Return a clean structured JSON response for a framework benchmark.",
        backstory=(
            "You are used only for testing whether CrewAI can run the same "
            "standardized benchmark task as LangGraph and OpenAI Agents SDK."
        ),
        llm=llm,
        tools=tools,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description=prompt,
        expected_output=(
            "Exactly one JSON object matching the schema specified in the task "
            "description above. No markdown. No extra text."
        ),
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)


def run_task(task: BenchmarkTask) -> AgentRunResult:
    start = time.perf_counter()
    medical_tools.reset_call_log()
    ecommerce_tools.reset_call_log()
    try:
        final_output = _run_agent(task.prompt, task.vertical)
        return AgentRunResult(
            task_id=task.task_id,
            framework=FRAMEWORK_NAME,
            vertical=task.vertical,
            final_output=final_output,
            latency_seconds=time.perf_counter() - start,
            success=True,
            tool_call_count=len(medical_tools.call_log) + len(ecommerce_tools.call_log),
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
