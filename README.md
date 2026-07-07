# Universal Agent Benchmark

## 1. Set up `.env`

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` and fill in your own API information:

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://your-proxy-api-domain/v1
OPENAI_MODEL=gpt-4

OPENAI_AGENTS_DISABLE_TRACING=1
CREWAI_DISABLE_TELEMETRY=true
OTEL_SDK_DISABLED=true
```

Do not share or upload your `.env` file.

## 2. Run the setup script

Create the three local Python environments and install dependencies:

```bash
./scripts/setup_envs.sh
```

This creates:

```text
.venv-openai
.venv-langgraph
.venv-crewai
```

## 3. Run the test

Run all smoke tests:

```bash
./scripts/run_smoke_tests.sh
```

Or run each framework separately:

```bash
source .venv-openai/bin/activate
python frameworks/openai_agents_sdk/run.py
deactivate
```

```bash
source .venv-langgraph/bin/activate
python frameworks/langgraph_agent/run.py
deactivate
```

```bash
source .venv-crewai/bin/activate
python frameworks/crewai_agent/run.py
deactivate
```
