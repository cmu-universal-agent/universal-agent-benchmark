import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

# CrewAI resolves its storage directory while the package is imported. Load
# local configuration first and keep its writable state inside the project so
# the adapter also works in sandboxed runners that cannot write to AppData.
load_dotenv(ROOT / ".env", override=False)
storage_dir = Path(os.getenv("CREWAI_STORAGE_DIR", ".crewai"))
if not storage_dir.is_absolute():
    storage_dir = ROOT / storage_dir
os.environ["CREWAI_STORAGE_DIR"] = str(storage_dir.resolve())

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from adapter.result_writer import append_result
from adapter.runtime import (
    GenerationSettings,
    GenerationSettingsResolution,
    configured_generation_settings,
    normalize_openai_model_settings,
    resolve_generation_settings,
    run_framework_task,
)
from adapter.schemas import AgentRunResult, BenchmarkTask
from adapter.task_loader import load_task
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "crewai"


@tool("search_literature")
def search_literature(pubmed_id: str) -> str:
    """Look up the research abstract for a given PubMed ID."""
    return medical_tools.search_literature(pubmed_id)


@tool("get_review_history")
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


def _build_llm(
    generation_settings: GenerationSettings,
) -> tuple[LLM, GenerationSettingsResolution]:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")

    # CrewAI often expects OpenAI models in this form:
    # openai/gpt-4, openai/gpt-4o-mini, etc.
    crewai_model_name = model_name if "/" in model_name else f"openai/{model_name}"
    supported_settings = normalize_openai_model_settings(
        crewai_model_name,
        generation_settings,
    )

    llm = LLM(
        model=crewai_model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=supported_settings.temperature,
        max_tokens=supported_settings.max_output_tokens,
        seed=supported_settings.seed,
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
    allowed_tools: list[str] | None,
    llm: LLM,
) -> tuple[str, dict[str, int]]:
    tools = _select_tools(vertical, allowed_tools)

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
    usage = result.token_usage
    return str(result), {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


def run_task(task: BenchmarkTask) -> AgentRunResult:
    return run_framework_task(
        task,
        framework=FRAMEWORK_NAME,
        package_name="crewai",
        tool_modules=[medical_tools, ecommerce_tools],
        requested_settings=configured_generation_settings(),
        build_model=_build_llm,
        run_model=lambda llm, _requested: _run_agent(
            task.prompt, task.vertical, task.allowed_tools, llm
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
