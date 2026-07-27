"""Shared runtime metadata and AgentRunResult construction.

Framework adapters use this module so model identity, framework version,
timestamps, raw output, and tool traces are recorded the same way for every
run. It deliberately leaves token counts as null until an adapter can obtain
provider-reported usage rather than estimating it inconsistently.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import uuid
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable, Sequence

from adapter.schemas import AgentRunResult, BenchmarkTask


ADAPTER_VERSION = "0.2.0"
TOOL_RESULT_MAX_BYTES = 50 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _optional_int(name: str) -> int | None:
    value = os.getenv(name)
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(name: str, default: float | None = None) -> float | None:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return float(value)


def _package_version(package_name: str) -> str | None:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


def _serialized_tool_result(value: Any) -> bytes:
    """Return the canonical UTF-8 representation used for result size/hash."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode("utf-8")


def _bounded_tool_result(value: Any) -> tuple[Any, bool, int, str | None]:
    """Cap a normalized tool result and preserve audit metadata.

    The preview is deliberately stored as a string inside a marker object so a
    truncated JSON object is never mistaken for a complete tool response.
    """
    payload = _serialized_tool_result(value)
    result_bytes = len(payload)
    if result_bytes <= TOOL_RESULT_MAX_BYTES:
        return value, False, result_bytes, None

    digest = hashlib.sha256(payload).hexdigest()
    preview_bytes = payload[: TOOL_RESULT_MAX_BYTES - 1024]
    preview = preview_bytes.decode("utf-8", errors="ignore")
    bounded: dict[str, str] = {
        "truncated_preview": preview,
        "truncation_notice": "Full serialized tool result exceeded 50KB.",
    }
    while len(_serialized_tool_result(bounded)) > TOOL_RESULT_MAX_BYTES:
        preview = preview[:-1024]
        bounded["truncated_preview"] = preview
    return bounded, True, result_bytes, digest


@dataclass(frozen=True)
class GenerationSettings:
    temperature: float | None
    max_output_tokens: int | None
    seed: int | None


@dataclass(frozen=True)
class GenerationSettingsResolution:
    requested: GenerationSettings
    effective: GenerationSettings
    unsupported: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunTiming:
    started_at: str
    started_perf_counter: float


def start_run_timing() -> RunTiming:
    """Start end-to-end timing before framework model construction."""
    return RunTiming(
        started_at=_utc_now(),
        started_perf_counter=time.perf_counter(),
    )


def resolve_generation_settings(
    requested: GenerationSettings,
    effective: GenerationSettings,
) -> GenerationSettingsResolution:
    """Separate requested settings from values retained by a model wrapper."""
    unsupported = tuple(
        field.name
        for field in fields(GenerationSettings)
        if getattr(requested, field.name) is not None
        and not _generation_value_matches(
            getattr(requested, field.name), getattr(effective, field.name)
        )
    )
    return GenerationSettingsResolution(
        requested=requested,
        effective=effective,
        unsupported=unsupported,
    )


def _generation_value_matches(
    requested: float | int, effective: float | int | None
) -> bool:
    """Compare a requested setting to its wrapper-echoed value.

    Some wrappers round-trip floats through their own coercion (e.g.
    pydantic), so exact equality would misreport a supported setting as
    unsupported due to float noise.
    """
    if effective is None:
        return False
    if isinstance(requested, float) or isinstance(effective, float):
        return math.isclose(requested, effective, rel_tol=0, abs_tol=1e-9)
    return requested == effective


def unsupported_generation_settings(
    requested: GenerationSettings,
) -> GenerationSettingsResolution:
    """Represent a model construction that applied no generation settings."""
    return resolve_generation_settings(
        requested,
        GenerationSettings(
            temperature=None,
            max_output_tokens=None,
            seed=None,
        ),
    )


def normalize_openai_model_settings(
    model_name: str,
    requested: GenerationSettings,
) -> GenerationSettings:
    """Omit known unsupported OpenAI model parameters.

    GPT-5 reasoning models reject non-default temperature values unless
    reasoning effort is explicitly disabled. The benchmark does not alter
    reasoning effort, so an unsupported requested temperature is omitted.
    """
    normalized_name = model_name.rsplit("/", 1)[-1].lower()
    temperature = requested.temperature
    if (
        normalized_name.startswith("gpt-5")
        and "chat" not in normalized_name
        and temperature not in (None, 1.0)
    ):
        temperature = None
    return GenerationSettings(
        temperature=temperature,
        max_output_tokens=requested.max_output_tokens,
        seed=requested.seed,
    )


def configured_generation_settings() -> GenerationSettings:
    """Read the generation settings shared by every framework adapter."""
    return GenerationSettings(
        temperature=_optional_float("OPENAI_TEMPERATURE", 0.0),
        max_output_tokens=_optional_int("OPENAI_MAX_OUTPUT_TOKENS"),
        seed=_optional_int("OPENAI_SEED"),
    )


@dataclass(frozen=True)
class RunContext:
    run_id: str
    experiment_id: str
    framework: str
    framework_version: str | None
    model_provider: str
    model_name: str
    model_version: str | None
    temperature: float | None
    max_output_tokens: int | None
    seed: int | None
    requested_generation_settings: GenerationSettings
    unsupported_generation_settings: tuple[str, ...]
    started_at: str
    started_perf_counter: float


def begin_run(
    framework: str,
    package_name: str,
    generation_settings: GenerationSettings | GenerationSettingsResolution | None = None,
    timing: RunTiming | None = None,
) -> RunContext:
    """Capture configuration at execution time, never during report generation."""
    run_timing = timing or start_run_timing()
    run_id = f"run-{uuid.uuid4().hex}"
    experiment_id = os.getenv("BENCHMARK_EXPERIMENT_ID") or f"manual-{run_id}"
    if isinstance(generation_settings, GenerationSettingsResolution):
        resolution = generation_settings
    else:
        settings = generation_settings or configured_generation_settings()
        resolution = resolve_generation_settings(settings, settings)
    effective_settings = resolution.effective
    return RunContext(
        run_id=run_id,
        experiment_id=experiment_id,
        framework=framework,
        framework_version=_package_version(package_name),
        model_provider=os.getenv("OPENAI_MODEL_PROVIDER", "openai"),
        model_name=os.getenv("OPENAI_MODEL", "unknown"),
        model_version=os.getenv("OPENAI_MODEL_VERSION") or None,
        temperature=effective_settings.temperature,
        max_output_tokens=effective_settings.max_output_tokens,
        seed=effective_settings.seed,
        requested_generation_settings=resolution.requested,
        unsupported_generation_settings=resolution.unsupported,
        started_at=run_timing.started_at,
        started_perf_counter=run_timing.started_perf_counter,
    )


def normalize_tool_calls(
    raw_logs: list[Any],
    run_id: str,
) -> list[dict[str, Any]]:
    """Convert shared mock-tool logs into the common tool-call shape.

    Legacy string-only logs remain readable so the adapters do not fail if an
    older tool module is used during migration.
    """
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_logs):
        if isinstance(raw, dict):
            row = dict(raw)
        else:
            row = {
                "tool_name": "unknown",
                "arguments": {"legacy_value": raw},
                "was_allowed": True,
                "arguments_valid": True,
                "started_at": None,
                "completed_at": None,
                "latency_ms": 0,
                "outcome": "success",
                "result": None,
                "error": None,
            }
        row.setdefault("schema_version", "1.0")
        row.setdefault("tool_call_id", f"tool-{uuid.uuid4().hex}")
        row["run_id"] = run_id
        row["sequence_index"] = index
        row.setdefault("retry_of", None)
        bounded, truncated, result_bytes, digest = _bounded_tool_result(
            row.get("result")
        )
        row["result"] = bounded
        row["result_truncated"] = truncated
        row["result_bytes"] = result_bytes
        row["result_sha256"] = digest
        normalized.append(row)
    return normalized


def finish_run(
    context: RunContext,
    task: BenchmarkTask,
    *,
    final_output: str,
    success: bool,
    error: str | None = None,
    raw_tool_logs: list[Any] | None = None,
    token_usage: dict[str, int | None] | None = None,
) -> AgentRunResult:
    """Build the same result envelope for every framework adapter."""
    raw_output = str(final_output or "")
    completed_at = _utc_now()
    tool_calls = normalize_tool_calls(raw_tool_logs or [], context.run_id)

    # Parse only for diagnostic metadata. Full task-specific JSON Schema
    # validation will be added after the schema field review is frozen.
    parsed_output: Any = None
    try:
        parsed_output = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError):
        pass

    usage = token_usage or {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }

    return AgentRunResult(
        task_id=task.task_id,
        framework=context.framework,
        vertical=task.vertical,
        final_output=raw_output,
        latency_seconds=time.perf_counter() - context.started_perf_counter,
        success=success,
        error=error,
        tool_call_count=len(tool_calls),
        raw_metadata={
            "adapter_version": ADAPTER_VERSION,
            "json_parse_valid": isinstance(parsed_output, dict),
            "requested_generation_settings": asdict(
                context.requested_generation_settings
            ),
            "effective_generation_settings": {
                "temperature": context.temperature,
                "max_output_tokens": context.max_output_tokens,
                "seed": context.seed,
            },
            "unsupported_generation_settings": list(
                context.unsupported_generation_settings
            ),
        },
        case_id=task.case_id,
        run_id=context.run_id,
        experiment_id=context.experiment_id,
        framework_version=context.framework_version,
        model_provider=context.model_provider,
        model_name=context.model_name,
        model_version=context.model_version,
        temperature=context.temperature,
        max_output_tokens=context.max_output_tokens,
        seed=context.seed,
        prompt_version=str(task.metadata.get("prompt_version", "legacy_prompt_v1")),
        started_at=context.started_at,
        completed_at=completed_at,
        raw_output=raw_output,
        tool_calls=tool_calls,
        token_usage=usage,
    )


def run_framework_task(
    task: BenchmarkTask,
    *,
    framework: str,
    package_name: str,
    tool_modules: Sequence[Any],
    requested_settings: GenerationSettings,
    build_model: Callable[[GenerationSettings], tuple[Any, GenerationSettingsResolution]],
    run_model: Callable[[Any, GenerationSettings], tuple[str, dict[str, int | None]]],
) -> AgentRunResult:
    """Shared run_task control flow for every framework adapter.

    ``requested_settings`` must be resolved by the caller (usually via
    ``configured_generation_settings()``) rather than read here, so
    framework modules can keep patching their own imported reference in
    tests. ``build_model`` receives the requested generation settings and
    returns the constructed model/agent object plus its resolved generation
    settings. A ``build_model`` failure is recorded as a model-construction
    error and ``run_model`` is never called. On success, ``run_model``
    receives the constructed object and the originally requested settings,
    and returns (final_output, token_usage). A ``run_model`` failure is
    recorded as a run error. ``tool_modules`` are reset before the attempt
    and their call logs are collected into the result regardless of outcome
    (except when model construction itself failed).
    """
    timing = start_run_timing()
    model_error: Exception | None = None
    model: Any = None
    try:
        model, generation_settings = build_model(requested_settings)
    except Exception as exc:
        model_error = exc
        generation_settings = unsupported_generation_settings(requested_settings)

    context = begin_run(framework, package_name, generation_settings, timing)
    for module in tool_modules:
        module.reset_call_log()

    if model_error is not None:
        return finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=f"{type(model_error).__name__}: {model_error}",
        )

    try:
        final_output, token_usage = run_model(model, requested_settings)
        return finish_run(
            context,
            task,
            final_output=final_output,
            success=True,
            raw_tool_logs=[log for module in tool_modules for log in module.call_log],
            token_usage=token_usage,
        )
    except Exception as exc:
        return finish_run(
            context,
            task,
            final_output="",
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            raw_tool_logs=[log for module in tool_modules for log in module.call_log],
        )
