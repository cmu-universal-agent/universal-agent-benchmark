import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

# CrewAI resolves storage and tracing dependencies while the package is
# imported. Keep both configurable state and its 1.15.1 credential store in a
# project-local directory so Windows/Linux runners do not require writes to a
# user profile outside the checkout.
load_dotenv(ROOT / ".env", override=False)
os.environ.setdefault("OPENAI_MODEL", "gpt-4")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
storage_dir = Path(os.getenv("CREWAI_STORAGE_DIR", ".crewai"))
if not storage_dir.is_absolute():
    storage_dir = ROOT / storage_dir
os.environ["CREWAI_STORAGE_DIR"] = str(storage_dir.resolve())

credential_dir = Path(
    os.getenv("CREWAI_CREDENTIAL_STORAGE_DIR", str(storage_dir / "credentials"))
)
if not credential_dir.is_absolute():
    credential_dir = ROOT / credential_dir
credential_dir = credential_dir.resolve()
credential_dir.mkdir(parents=True, exist_ok=True)
try:
    credential_dir.chmod(0o700)
except OSError:
    pass

# CrewAI 1.15.1 has no environment variable for this path and initializes the
# token manager even when tracing is disabled. Patch only that path provider;
# encryption, atomic writes, permissions, and token handling stay in CrewAI.
from crewai_core.token_manager import TokenManager

TokenManager._get_secure_storage_path = staticmethod(lambda: credential_dir)

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from adapter.result_writer import append_result
from adapter.runtime import RunContext, begin_run, finish_run
from adapter.schemas import AgentRunResult, BenchmarkTask
from adapter.task_loader import load_task
from verticals.ecommerce_trend_research import tools as ecommerce_tools
from verticals.medical_diagnostic import tools as medical_tools

TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"
FRAMEWORK_NAME = "crewai"
_EXTRA_USAGE_FIELDS = (
    "cached_prompt_tokens",
    "reasoning_tokens",
    "cache_creation_tokens",
    "successful_requests",
)


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


def _usage_value(usage: Any, name: str) -> int | None:
    """Read one non-negative integer without assuming a field is present."""
    try:
        value = getattr(usage, name)
    except (AttributeError, TypeError, ValueError):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _extract_token_usage(
    crew_output: Any,
) -> tuple[dict[str, int | None], dict[str, Any]]:
    """Normalize CrewAI usage and distinguish missing usage from real zeroes."""
    unavailable = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }
    try:
        usage = crew_output.token_usage
    except (AttributeError, TypeError, ValueError):
        return unavailable, {"available": False, "crew_fields": {}}
    if usage is None:
        return unavailable, {"available": False, "crew_fields": {}}

    prompt = _usage_value(usage, "prompt_tokens")
    completion = _usage_value(usage, "completion_tokens")
    total = _usage_value(usage, "total_tokens")
    requests = _usage_value(usage, "successful_requests")
    if requests in (0, None) and all(
        value in (0, None) for value in (prompt, completion, total)
    ):
        return unavailable, {"available": False, "crew_fields": {}}
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    extra = {
        name: value
        for name in _EXTRA_USAGE_FIELDS
        if (value := _usage_value(usage, name)) is not None
    }
    return {
        "input_tokens": prompt,
        "output_tokens": completion,
        "total_tokens": total,
    }, {"available": True, "crew_fields": extra}


def _llm_configuration(context: RunContext) -> tuple[dict[str, Any], list[str]]:
    """Build arguments accepted by the installed CrewAI 1.15.1 LLM."""
    kwargs: dict[str, Any] = {
        "model": context.model_name,
        "provider": context.model_provider,
        "temperature": context.temperature,
    }
    forwarded = ["model", "provider", "temperature"]
    if api_key := os.getenv("OPENAI_API_KEY"):
        kwargs["api_key"] = api_key
    if base_url := os.getenv("OPENAI_BASE_URL"):
        kwargs["base_url"] = base_url
    if context.max_output_tokens is not None:
        kwargs["max_tokens"] = context.max_output_tokens
        forwarded.append("max_output_tokens_as_max_tokens")
    if context.seed is not None:
        kwargs["seed"] = context.seed
        forwarded.append("seed")
    return kwargs, forwarded


def _redacted_error(exc: Exception) -> str:
    """Keep useful exception details while removing likely credentials."""
    message = str(exc)
    for name, value in os.environ.items():
        if value and len(value) >= 8 and any(
            marker in name.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD")
        ):
            message = message.replace(value, "[REDACTED]")
    message = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", message)
    message = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED]", message)
    message = re.sub(r"(https?://)[^/@\s]+@", r"\1[REDACTED]@", message)
    message = re.sub(
        r"(?i)([?&](?:api_?key|token|access_?token|secret|password)=)[^&\s]+",
        r"\1[REDACTED]",
        message,
    )
    return f"{type(exc).__name__}: {message}"


def _run_agent(
    prompt: str,
    vertical: str,
    allowed_tools: list[str] | None = None,
    context: RunContext | None = None,
) -> tuple[str, dict[str, int | None], dict[str, Any]]:
    context = context or begin_run(FRAMEWORK_NAME, "crewai")
    llm_kwargs, forwarded_settings = _llm_configuration(context)
    llm = LLM(**llm_kwargs)
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
    crew_output = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    ).kickoff()
    token_usage, usage_metadata = _extract_token_usage(crew_output)
    return str(crew_output), token_usage, {
        "crewai_token_usage": usage_metadata,
        "generation_settings_forwarded_to_crewai": forwarded_settings,
        "selected_tool_names": [getattr(value, "name", "unknown") for value in tools],
    }


def _raw_tool_logs() -> list[Any]:
    return [*medical_tools.call_log, *ecommerce_tools.call_log]


def run_task(task: BenchmarkTask) -> AgentRunResult:
    context = begin_run(FRAMEWORK_NAME, "crewai")
    _, forwarded_settings = _llm_configuration(context)
    medical_tools.reset_call_log()
    ecommerce_tools.reset_call_log()
    try:
        final_output, token_usage, crewai_metadata = _run_agent(
            task.prompt, task.vertical, task.allowed_tools, context
        )
        result = finish_run(
            context,
            task,
            final_output=final_output,
            success=True,
            raw_tool_logs=_raw_tool_logs(),
            token_usage=token_usage,
        )
        result.raw_metadata.update(crewai_metadata)
        return result
    except Exception as exc:
        result = finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=_redacted_error(exc),
            raw_tool_logs=_raw_tool_logs(),
        )
        result.raw_metadata.update(
            {
                "crewai_token_usage": {"available": False, "crew_fields": {}},
                "generation_settings_forwarded_to_crewai": forwarded_settings,
            }
        )
        return result


def main() -> None:
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
