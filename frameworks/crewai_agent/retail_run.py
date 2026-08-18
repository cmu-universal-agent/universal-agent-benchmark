"""CrewAI thin wrapper for the WS3 retail vertical (tau-retail / E5)."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapter.result_writer import append_result
from adapter.e5_session import E5_AGENT_SYSTEM_PROMPT, run_e5_session
from adapter.tau_retail_env import make_retail_env
from adapter.runtime import (
    GenerationSettings,
    RunContext,
    begin_run,
    configured_generation_settings,
    failed_model_construction_settings,
    finish_run,
    start_run_timing,
)
from adapter.schemas import AgentRunResult, BenchmarkTask
from frameworks.crewai_agent import run as crewai_run
from frameworks.crewai_agent.retail_tools import make_retail_tools

DATA_DIR = str(ROOT / "verticals" / "retail")
FRAMEWORK_NAME = "crewai"
WRAPPER_VERSION = "0.1.0"
MAX_RETAIL_ITERATIONS = 4


def _system_prompt() -> str:
    return E5_AGENT_SYSTEM_PROMPT


def _run_retail_agent(
    llm: Any,
    env: RetailEnv,
    prompt: str,
    allowed_tools: list[str] | None,
) -> tuple[
    str,
    dict[str, int | None],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
]:
    tools = make_retail_tools(env, allowed_tools)
    agent = crewai_run.Agent(
        role="Retail E5 Agent",
        goal="Resolve the retail request and return the required JSON response.",
        backstory=_system_prompt(),
        llm=llm,
        tools=tools,
        verbose=False,
        allow_delegation=False,
        max_iter=MAX_RETAIL_ITERATIONS,
    )
    task = crewai_run.Task(
        description=prompt,
        expected_output=(
            "Exactly one JSON object matching the public E5 output schema. "
            "No markdown and no extra text."
        ),
        agent=agent,
    )
    crew_output = crewai_run.Crew(
        agents=[agent],
        tasks=[task],
        process=crewai_run.Process.sequential,
        verbose=False,
    ).kickoff()
    token_usage, usage_metadata = crewai_run._extract_token_usage(crew_output)
    return (
        str(crew_output),
        token_usage,
        usage_metadata,
        env.get_trace(),
        env.get_final_state(),
    )


def _requested_settings(seed: int | None) -> GenerationSettings:
    configured = configured_generation_settings()
    if seed is None:
        return configured
    return GenerationSettings(
        temperature=configured.temperature,
        max_output_tokens=configured.max_output_tokens,
        seed=seed,
    )


def _start_retail_run(
    requested_settings: GenerationSettings,
) -> tuple[Any, Exception | None, RunContext]:
    timing = start_run_timing()
    try:
        llm, settings_resolution = crewai_run._build_llm(requested_settings)
        model_error = None
    except Exception as exc:
        llm = None
        model_error = exc
        settings_resolution = failed_model_construction_settings(requested_settings)

    context = begin_run(
        FRAMEWORK_NAME,
        "crewai",
        settings_resolution,
        timing,
        model_construction_failed=model_error is not None,
    )
    return llm, model_error, context


def _execute_retail_task(
    context: RunContext,
    task: BenchmarkTask,
    llm: Any,
) -> AgentRunResult:
    environment_seed = context.seed if context.seed is not None else 42
    env = make_retail_env(task, data_dir=DATA_DIR, seed=environment_seed)
    try:
        env.reset(
            task.case_id,
            reset_id=f"run-{uuid.uuid4().hex}",
            seed=environment_seed,
        )
        session = None
        usage_metadata = {}
        if task.task_id == "E5":
            def run_turn(prompt: str):
                output, usage, _, _, _ = _run_retail_agent(
                    llm,
                    env,
                    prompt,
                    task.allowed_tools,
                )
                return output, usage

            session = run_e5_session(task, run_turn)
            final_output = session.final_output
            token_usage = session.token_usage
            tool_trace = env.get_trace()
            final_state = env.get_final_state()
        else:
            (
                final_output,
                token_usage,
                usage_metadata,
                tool_trace,
                final_state,
            ) = _run_retail_agent(
                llm,
                env,
                task.prompt,
                task.allowed_tools,
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
                "crewai_token_usage": usage_metadata,
            }
        )
        if session is not None:
            result.raw_metadata.update(
                {
                    "assistant_turns": session.assistant_turns,
                    "user_simulator": session.simulator,
                }
            )
        return result
    except Exception as exc:
        tool_trace = env.get_trace() if env.case_id else []
        result = finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            raw_tool_logs=tool_trace,
        )
        result.raw_metadata["wrapper_version"] = WRAPPER_VERSION
        if env.case_id:
            result.raw_metadata["final_state"] = env.get_final_state()
        return result


def run_retail_task(task: BenchmarkTask, *, seed: int | None = None) -> AgentRunResult:
    """Run one retail benchmark case through CrewAI and the shared RetailEnv."""
    if not task.case_id:
        raise ValueError("retail tasks require case_id")

    llm, model_error, context = _start_retail_run(_requested_settings(seed))
    if model_error is None:
        return _execute_retail_task(context, task, llm)

    result = finish_run(
        context,
        task,
        final_output="",
        success=False,
        error=f"{type(model_error).__name__}: {model_error}",
    )
    result.raw_metadata["wrapper_version"] = WRAPPER_VERSION
    return result


def build_wrapper_evidence() -> dict[str, Any]:
    from frameworks.crewai_agent.retail_evidence import build_wrapper_evidence as _build

    return _build()


def main() -> None:
    import argparse

    from adapter.task_loader import load_task

    parser = argparse.ArgumentParser(
        description="Run a retail case via CrewAI and the shared RetailEnv."
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
