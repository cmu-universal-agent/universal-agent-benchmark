import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

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
from adapter.vertical_routing import select_vertical_tools
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "openai_agents_sdk"

load_dotenv(ROOT / ".env", override=False)

# Disable OpenAI Agents SDK tracing when using proxy API
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

from agents import (
    Agent,
    AgentOutputSchema,
    ModelSettings,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)

def _configure_openai_client() -> None:
    set_default_openai_api("chat_completions")
    set_default_openai_client(
        AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
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
    return select_vertical_tools(TOOLS_BY_VERTICAL, vertical, allowed_tools)


def _build_agent(
    vertical: str,
    allowed_tools: list[str] | None,
    generation_settings: GenerationSettings,
) -> tuple[Agent, GenerationSettingsResolution]:
    _configure_openai_client()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")
    supported_settings = normalize_openai_model_settings(
        model_name,
        generation_settings,
    )
    tools = _select_tools(vertical, allowed_tools)
    extra_args = (
        {"seed": supported_settings.seed}
        if supported_settings.seed is not None
        else None
    )
    agent = Agent(
        name="OpenAI Smoke Test Agent",
        instructions=(
            "You are a benchmark smoke-test agent. "
            "Follow the user's output format exactly. "
            "Do not add markdown."
        ),
        model=model_name,
        model_settings=ModelSettings(
            temperature=supported_settings.temperature,
            max_tokens=supported_settings.max_output_tokens,
            extra_args=extra_args,
        ),
        output_type=AgentOutputSchema(
            dict[str, object],
            strict_json_schema=False,
        ),
        tools=tools,
    )
    model_settings = agent.model_settings
    effective_settings = GenerationSettings(
        temperature=model_settings.temperature,
        max_output_tokens=model_settings.max_tokens,
        seed=(model_settings.extra_args or {}).get("seed"),
    )
    return agent, resolve_generation_settings(
        generation_settings,
        effective_settings,
    )


async def _run_agent(
    prompt: str,
    agent: Agent,
) -> tuple[str, dict[str, int]]:
    result = await Runner.run(agent, prompt)
    usage = result.context_wrapper.usage
    return json.dumps(result.final_output, ensure_ascii=False), {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }


def run_task(task: BenchmarkTask) -> AgentRunResult:
    if task.vertical == "retail":
        from frameworks.openai_agents_sdk.retail_run import run_retail_task

        return run_retail_task(task)

    return run_framework_task(
        task,
        framework=FRAMEWORK_NAME,
        package_name="openai-agents",
        tool_modules=[medical_tools, ecommerce_tools],
        requested_settings=configured_generation_settings(),
        build_model=lambda settings: _build_agent(
            task.vertical, task.allowed_tools, settings
        ),
        run_model=lambda agent, _requested: asyncio.run(_run_agent(task.prompt, agent)),
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
