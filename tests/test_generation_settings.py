import importlib
import importlib.util
import os
import unittest
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

from adapter.runtime import (
    GenerationSettings,
    begin_run,
    configured_generation_settings,
    resolve_generation_settings,
    run_framework_task,
    start_run_timing,
)
from adapter.schemas import BenchmarkTask


OPENAI_AGENTS_AVAILABLE = importlib.util.find_spec("agents") is not None
LANGGRAPH_AVAILABLE = importlib.util.find_spec("langgraph") is not None
CREWAI_AVAILABLE = importlib.util.find_spec("crewai") is not None


def _task() -> BenchmarkTask:
    return BenchmarkTask(
        task_id="SMOKE-001",
        vertical="smoke_test",
        prompt="Return JSON.",
    )


def _settings() -> GenerationSettings:
    return GenerationSettings(
        temperature=0.25,
        max_output_tokens=321,
        seed=17,
    )


def _import_runner(module_name: str):
    with patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "test-model",
            "CREWAI_DISABLE_TELEMETRY": "true",
            "OTEL_SDK_DISABLED": "true",
        },
    ):
        return importlib.import_module(module_name)


class SharedGenerationSettingsTests(unittest.TestCase):
    def test_reads_shared_environment_settings(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_TEMPERATURE": "0.25",
                "OPENAI_MAX_OUTPUT_TOKENS": "321",
                "OPENAI_SEED": "17",
            },
            clear=False,
        ):
            self.assertEqual(configured_generation_settings(), _settings())

    def test_begin_run_records_passed_effective_settings(self):
        settings = _settings()
        with patch.dict(
            os.environ,
            {
                "OPENAI_TEMPERATURE": "1.5",
                "OPENAI_MAX_OUTPUT_TOKENS": "999",
                "OPENAI_SEED": "999",
            },
            clear=False,
        ):
            context = begin_run("test", "missing-test-package", settings)

        self.assertEqual(context.temperature, settings.temperature)
        self.assertEqual(context.max_output_tokens, settings.max_output_tokens)
        self.assertEqual(context.seed, settings.seed)

    def test_unconfigured_optional_settings_remain_null(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_TEMPERATURE": "",
                "OPENAI_MAX_OUTPUT_TOKENS": "",
                "OPENAI_SEED": "",
            },
            clear=False,
        ):
            settings = configured_generation_settings()

        self.assertEqual(settings.temperature, 0.0)
        self.assertIsNone(settings.max_output_tokens)
        self.assertIsNone(settings.seed)

    def test_begin_run_preserves_preconstruction_timing(self):
        timing = start_run_timing()

        context = begin_run(
            "test",
            "missing-test-package",
            _settings(),
            timing,
        )

        self.assertEqual(context.started_at, timing.started_at)
        self.assertEqual(
            context.started_perf_counter,
            timing.started_perf_counter,
        )


class ResolveGenerationSettingsTests(unittest.TestCase):
    def test_float_round_trip_noise_is_not_flagged_unsupported(self):
        requested = GenerationSettings(
            temperature=0.7,
            max_output_tokens=321,
            seed=17,
        )
        effective = GenerationSettings(
            temperature=0.6999999999999998,
            max_output_tokens=321,
            seed=17,
        )

        resolution = resolve_generation_settings(requested, effective)

        self.assertEqual(resolution.unsupported, ())

    def test_genuinely_different_temperature_is_flagged_unsupported(self):
        requested = GenerationSettings(
            temperature=0.7,
            max_output_tokens=321,
            seed=17,
        )
        effective = GenerationSettings(
            temperature=None,
            max_output_tokens=321,
            seed=17,
        )

        resolution = resolve_generation_settings(requested, effective)

        self.assertEqual(resolution.unsupported, ("temperature",))


class RunFrameworkTaskModelConstructionTests(unittest.TestCase):
    def test_build_model_failure_is_not_reported_as_unsupported_settings(self):
        def _build_model_raises(_settings):
            raise RuntimeError("invalid API key")

        def _run_model_never_called(_model, _settings):
            self.fail("run_model must not be called when build_model fails")

        result = run_framework_task(
            _task(),
            framework="test",
            package_name="missing-test-package",
            tool_modules=(),
            requested_settings=_settings(),
            build_model=_build_model_raises,
            run_model=_run_model_never_called,
        )

        self.assertFalse(result.success)
        self.assertIn("invalid API key", result.error)
        self.assertEqual(
            result.raw_metadata["unsupported_generation_settings"], []
        )
        self.assertTrue(result.raw_metadata["model_construction_failed"])

    def test_run_model_failure_does_not_set_model_construction_failed(self):
        def _build_model_ok(settings):
            return object(), resolve_generation_settings(settings, settings)

        def _run_model_raises(_model, _settings):
            raise RuntimeError("agent run blew up")

        result = run_framework_task(
            _task(),
            framework="test",
            package_name="missing-test-package",
            tool_modules=(),
            requested_settings=_settings(),
            build_model=_build_model_ok,
            run_model=_run_model_raises,
        )

        self.assertFalse(result.success)
        self.assertIn("agent run blew up", result.error)
        self.assertFalse(result.raw_metadata["model_construction_failed"])

    def test_run_model_metadata_is_added_to_result(self):
        def _build_model_ok(settings):
            return object(), resolve_generation_settings(settings, settings)

        result = run_framework_task(
            _task(),
            framework="test",
            package_name="missing-test-package",
            tool_modules=(),
            requested_settings=_settings(),
            build_model=_build_model_ok,
            run_model=lambda _model, _settings: (
                "{}",
                {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
                {"wrapper_detail": "recorded"},
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.raw_metadata["wrapper_detail"], "recorded")


@unittest.skipUnless(
    OPENAI_AGENTS_AVAILABLE,
    "OpenAI Agents SDK is not installed in this virtual environment",
)
class OpenAIAgentsGenerationSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _import_runner("frameworks.openai_agents_sdk.run")

    def test_passes_every_recorded_setting_to_model(self):
        settings = _settings()
        with patch.object(
            self.runner.Agent,
            "__init__",
            side_effect=RuntimeError("stop after model construction"),
        ) as constructor:
            with self.assertRaisesRegex(RuntimeError, "model construction"):
                self.runner._build_agent("smoke_test", [], settings)

        model_settings = constructor.call_args.kwargs["model_settings"]
        self.assertEqual(model_settings.temperature, settings.temperature)
        self.assertEqual(model_settings.max_tokens, settings.max_output_tokens)
        self.assertEqual(model_settings.extra_args, {"seed": settings.seed})

    def test_run_log_uses_settings_passed_to_agent(self):
        settings = _settings()
        run_agent = AsyncMock(return_value=("{}", {}))
        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "gpt-4",
                },
                clear=False,
            ),
            patch.object(
                self.runner,
                "configured_generation_settings",
                return_value=settings,
            ),
            patch.object(self.runner, "_run_agent", run_agent),
        ):
            result = self.runner.run_task(_task())

        run_agent.assert_awaited_once_with("Return JSON.", ANY)
        self.assertEqual(result.temperature, settings.temperature)
        self.assertEqual(result.max_output_tokens, settings.max_output_tokens)
        self.assertEqual(result.seed, settings.seed)
        self.assertEqual(result.raw_metadata["unsupported_generation_settings"], [])

    def test_gpt5_omits_known_unsupported_temperature(self):
        requested = GenerationSettings(
            temperature=0.0,
            max_output_tokens=321,
            seed=17,
        )
        run_agent = AsyncMock(return_value=("{}", {}))
        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "gpt-5",
                },
                clear=False,
            ),
            patch.object(
                self.runner,
                "configured_generation_settings",
                return_value=requested,
            ),
            patch.object(self.runner, "_run_agent", run_agent),
        ):
            result = self.runner.run_task(_task())

        constructed_agent = run_agent.await_args.args[1]
        self.assertIsNone(constructed_agent.model_settings.temperature)
        self.assertIsNone(result.temperature)
        self.assertEqual(
            result.raw_metadata["unsupported_generation_settings"],
            ["temperature"],
        )


@unittest.skipUnless(
    LANGGRAPH_AVAILABLE,
    "LangGraph is not installed in this virtual environment",
)
class LangGraphGenerationSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _import_runner("frameworks.langgraph_agent.run")

    def test_passes_every_recorded_setting_to_model(self):
        settings = _settings()
        with patch.object(
            self.runner,
            "ChatOpenAI",
            side_effect=RuntimeError("stop after model construction"),
        ) as constructor:
            with self.assertRaisesRegex(RuntimeError, "model construction"):
                self.runner._build_llm(settings)

        constructor.assert_called_once()
        kwargs = constructor.call_args.kwargs
        self.assertEqual(kwargs["temperature"], settings.temperature)
        self.assertEqual(kwargs["max_tokens"], settings.max_output_tokens)
        self.assertEqual(kwargs["seed"], settings.seed)

    def test_run_log_uses_settings_passed_to_agent(self):
        settings = _settings()
        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "gpt-4",
                },
                clear=False,
            ),
            patch.object(
                self.runner,
                "configured_generation_settings",
                return_value=settings,
            ),
            patch.object(
                self.runner,
                "_run_agent",
                return_value=("{}", {}),
            ) as run_agent,
        ):
            result = self.runner.run_task(_task())

        run_agent.assert_called_once_with(
            "Return JSON.",
            "smoke_test",
            None,
            settings,
            ANY,
        )
        self.assertEqual(result.temperature, settings.temperature)
        self.assertEqual(result.max_output_tokens, settings.max_output_tokens)
        self.assertEqual(result.seed, settings.seed)

    def test_token_usage_preserves_missing_fields(self):
        usage = self.runner._extract_token_usage(
            [
                SimpleNamespace(
                    usage_metadata={"input_tokens": 4, "output_tokens": 2}
                ),
                SimpleNamespace(usage_metadata={"input_tokens": 3}),
            ]
        )

        self.assertEqual(
            usage,
            {"input_tokens": 7, "output_tokens": 2, "total_tokens": 9},
        )

    def test_gpt5_records_real_wrapper_normalization(self):
        from langchain_core.messages import AIMessage

        class OfflineGraph:
            config = None

            def invoke(self, _state, config=None):
                self.config = config
                return {"messages": [AIMessage(content="{}")]}

        offline_graph = OfflineGraph()
        requested = GenerationSettings(
            temperature=0.0,
            max_output_tokens=321,
            seed=17,
        )
        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "gpt-5",
                },
                clear=False,
            ),
            patch.object(
                self.runner,
                "configured_generation_settings",
                return_value=requested,
            ),
            patch.object(
                self.runner.StateGraph,
                "compile",
                return_value=offline_graph,
            ),
        ):
            result = self.runner.run_task(_task())

        self.assertTrue(result.success, result.error)
        self.assertEqual(
            offline_graph.config,
            {"recursion_limit": self.runner.RECURSION_LIMIT},
        )
        self.assertIsNone(result.temperature)
        self.assertEqual(result.max_output_tokens, 321)
        self.assertEqual(result.seed, 17)
        self.assertEqual(
            result.raw_metadata["requested_generation_settings"],
            {
                "temperature": 0.0,
                "max_output_tokens": 321,
                "seed": 17,
            },
        )
        self.assertEqual(
            result.raw_metadata["effective_generation_settings"],
            {
                "temperature": None,
                "max_output_tokens": 321,
                "seed": 17,
            },
        )
        self.assertEqual(
            result.raw_metadata["unsupported_generation_settings"],
            ["temperature"],
        )


@unittest.skipUnless(
    CREWAI_AVAILABLE,
    "CrewAI is not installed in this virtual environment",
)
class CrewAIGenerationSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _import_runner("frameworks.crewai_agent.run")

    def test_passes_every_recorded_setting_to_model(self):
        settings = _settings()
        with patch.object(
            self.runner,
            "LLM",
            side_effect=RuntimeError("stop after model construction"),
        ) as constructor:
            with self.assertRaisesRegex(RuntimeError, "model construction"):
                self.runner._build_llm(settings)

        constructor.assert_called_once()
        kwargs = constructor.call_args.kwargs
        self.assertEqual(kwargs["temperature"], settings.temperature)
        self.assertEqual(kwargs["max_tokens"], settings.max_output_tokens)
        self.assertEqual(kwargs["seed"], settings.seed)

    def test_run_log_uses_settings_passed_to_agent(self):
        settings = _settings()
        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "gpt-4",
                },
                clear=False,
            ),
            patch.object(
                self.runner,
                "configured_generation_settings",
                return_value=settings,
            ),
            patch.object(
                self.runner,
                "_run_agent",
                return_value=("{}", {}),
            ) as run_agent,
        ):
            result = self.runner.run_task(_task())

        run_agent.assert_called_once_with(
            "Return JSON.",
            "smoke_test",
            None,
            ANY,
        )
        self.assertEqual(result.temperature, settings.temperature)
        self.assertEqual(result.max_output_tokens, settings.max_output_tokens)
        self.assertEqual(result.seed, settings.seed)
        self.assertEqual(result.raw_metadata["unsupported_generation_settings"], [])

    def test_gpt5_omits_known_unsupported_temperature(self):
        requested = GenerationSettings(
            temperature=0.0,
            max_output_tokens=321,
            seed=17,
        )
        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "gpt-5",
                },
                clear=False,
            ),
            patch.object(
                self.runner,
                "configured_generation_settings",
                return_value=requested,
            ),
            patch.object(
                self.runner,
                "_run_agent",
                return_value=("{}", {}),
            ) as run_agent,
        ):
            result = self.runner.run_task(_task())

        constructed_llm = run_agent.call_args.args[3]
        self.assertIsNone(constructed_llm.temperature)
        self.assertIsNone(result.temperature)
        self.assertEqual(
            result.raw_metadata["unsupported_generation_settings"],
            ["temperature"],
        )


if __name__ == "__main__":
    unittest.main()
