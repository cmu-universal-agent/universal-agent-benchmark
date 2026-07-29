"""OpenAI Agents SDK thin wrapper for the WS3 retail vertical (tau-retail / E5)."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

from adapter.result_writer import append_result
from adapter.runtime import begin_run, finish_run
from adapter.schemas import AgentRunResult, BenchmarkTask
from adapter.retail_core.env import RetailEnv
from frameworks.openai_agents_sdk.retail_tools import make_retail_tools

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = str(ROOT / "verticals" / "retail")
FRAMEWORK_NAME = "openai_agents_sdk"
WRAPPER_VERSION = "0.1.0"


def _system_prompt() -> str:
    return (
        "You are a retail customer-support agent. Use the provided tools to resolve "
        "the customer's issue. Follow policy and only use allowed tools. "
        "When finished, reply with a single JSON object (no markdown) containing "
        'at least "resolution" (string) and "actions_taken" (array of strings).'
    )


def _configure_openai_client() -> None:
    """Match the legacy smoke-test runner's OpenAI Agents SDK setup."""
    from openai import AsyncOpenAI

    from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled

    os.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "1")
    set_default_openai_api("chat_completions")
    set_default_openai_client(
        AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        ),
        use_for_tracing=False,
    )
    set_tracing_disabled(True)


async def _run_retail_agent(
    env: RetailEnv,
    prompt: str,
    allowed_tools: list[str] | None,
) -> tuple[str, dict[str, int | None], list[dict[str, Any]], dict[str, Any]]:
    from agents import Agent, Runner

    _configure_openai_client()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")
    tools = make_retail_tools(env, allowed_tools)
    agent = Agent(
        name="Retail E5 Agent",
        instructions=_system_prompt(),
        model=model_name,
        tools=tools,
    )
    result = await Runner.run(agent, prompt)
    usage = result.context_wrapper.usage
    token_usage = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }
    return str(result.final_output), token_usage, env.get_trace(), env.get_final_state()


def run_retail_task(task: BenchmarkTask, *, seed: int | None = None) -> AgentRunResult:
    """Run one retail benchmark case through OpenAI Agents SDK + RetailEnv."""
    if not task.case_id:
        raise ValueError("retail tasks require case_id")

    context = begin_run(FRAMEWORK_NAME, "openai-agents")
    env = RetailEnv(data_dir=DATA_DIR, seed=seed or task.seed or 42)
    run_seed = seed if seed is not None else task.seed

    try:
        env.reset(
            task.case_id,
            reset_id=f"run-{uuid.uuid4().hex}",
            seed=run_seed or 42,
        )
        final_output, token_usage, tool_trace, final_state = asyncio.run(
            _run_retail_agent(env, task.prompt, task.allowed_tools)
        )
        result = finish_run(
            context,
            task,
            final_output=final_output,
            success=True,
            raw_tool_logs=tool_trace,
            token_usage=token_usage,
        )
        result.raw_metadata.update(
            {
                "wrapper_version": WRAPPER_VERSION,
                "final_state": final_state,
            }
        )
        return result
    except Exception as exc:
        tool_trace = env.get_trace() if env.case_id else []
        return finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            raw_tool_logs=tool_trace,
        )


def build_wrapper_evidence() -> dict[str, Any]:
    from frameworks.openai_agents_sdk.retail_evidence import build_wrapper_evidence as _build

    return _build()


def main() -> None:
    import argparse
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from adapter.task_loader import load_task

    parser = argparse.ArgumentParser(
        description="Run a retail case via OpenAI Agents SDK + RetailEnv."
    )
    parser.add_argument(
        "--task",
        type=Path,
        default=ROOT / "verticals" / "retail" / "cases" / "RETAIL-E5-001.json",
    )
    parser.add_argument(
        "--write-evidence",
        type=Path,
        default=None,
        help="Write offline wrapper-evidence JSON and exit (no LLM).",
    )
    args = parser.parse_args()

    if args.write_evidence:
        evidence = build_wrapper_evidence()
        args.write_evidence.parent.mkdir(parents=True, exist_ok=True)
        args.write_evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(f"wrote wrapper evidence to {args.write_evidence}")
        return

    task = load_task(args.task)
    result = run_retail_task(task)
    append_result(result)

    print(f"\n=== {FRAMEWORK_NAME} retail Result ===")
    print(f"success={result.success} latency={result.latency_seconds:.2f}s")
    print(result.final_output or result.error)


if __name__ == "__main__":
    main()
