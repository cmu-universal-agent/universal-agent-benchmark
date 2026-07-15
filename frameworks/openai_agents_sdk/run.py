import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.runtime import begin_run, finish_run
from adapter.schemas import AgentRunResult, BenchmarkTask
from adapter.task_loader import load_task
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "openai_agents_sdk"

load_dotenv(ROOT / ".env", override=False)

# Disable OpenAI Agents SDK tracing when using proxy API
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model = os.getenv("OPENAI_MODEL", "gpt-4")

set_default_openai_api("chat_completions")

set_default_openai_client(
    AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    ),
    use_for_tracing=False,
)

set_tracing_disabled(True)


@function_tool
def search_literature(pubmed_id: str) -> str:
    """Look up the research abstract for a given PubMed ID."""
    return medical_tools.search_literature(pubmed_id)


@function_tool
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


async def _run_agent(
    prompt: str, vertical: str, allowed_tools: list[str] | None = None
) -> str:
    tools = _select_tools(vertical, allowed_tools)
    agent = Agent(
        name="OpenAI Smoke Test Agent",
        instructions=(
            "You are a benchmark smoke-test agent. "
            "Follow the user's output format exactly. "
            "Do not add markdown."
        ),
        model=model,
        tools=tools,
    )
    result = await Runner.run(agent, prompt)
    return result.final_output


def run_task(task: BenchmarkTask) -> AgentRunResult:
    context = begin_run(FRAMEWORK_NAME, "openai-agents")
    medical_tools.reset_call_log()
    ecommerce_tools.reset_call_log()
    try:
        final_output = asyncio.run(
            _run_agent(task.prompt, task.vertical, task.allowed_tools)
        )
        return finish_run(
            context,
            task,
            final_output=final_output,
            success=True,
            raw_tool_logs=[*medical_tools.call_log, *ecommerce_tools.call_log],
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
