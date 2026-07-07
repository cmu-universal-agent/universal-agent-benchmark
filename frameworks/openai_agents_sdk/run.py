import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parents[2]
TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"

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


async def main():
    with open(TASK_PATH, "r", encoding="utf-8") as f:
        task = json.load(f)

    agent = Agent(
        name="OpenAI Smoke Test Agent",
        instructions=(
            "You are a benchmark smoke-test agent. "
            "Follow the user's output format exactly. "
            "Do not add markdown."
        ),
        model=model,
    )

    result = await Runner.run(agent, task["prompt"])

    print("\n=== OpenAI Agents SDK Result ===")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())