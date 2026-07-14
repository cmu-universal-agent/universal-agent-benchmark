import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.schemas import AgentRunResult, BenchmarkTask

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "openai_agents_sdk"

load_dotenv(ROOT / ".env", override=True)

# Disable OpenAI Agents SDK tracing when using proxy API
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

from agents import (
    Agent,
    Runner,
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


async def _run_agent(prompt: str) -> str:
    agent = Agent(
        name="OpenAI Smoke Test Agent",
        instructions=(
            "You are a benchmark smoke-test agent. "
            "Follow the user's output format exactly. "
            "Do not add markdown."
        ),
        model=model,
    )
    result = await Runner.run(agent, prompt)
    return result.final_output


def run_task(task: BenchmarkTask) -> AgentRunResult:
    start = time.perf_counter()
    try:
        final_output = asyncio.run(_run_agent(task.prompt))
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
