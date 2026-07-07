#!/bin/bash
set -e

echo "Running OpenAI Agents SDK smoke test..."
source .venv-openai/bin/activate
python frameworks/openai_agents_sdk/run.py
deactivate

echo ""
echo "Running LangGraph smoke test..."
source .venv-langgraph/bin/activate
python frameworks/langgraph_agent/run.py
deactivate

echo ""
echo "Running CrewAI smoke test..."
source .venv-crewai/bin/activate
python frameworks/crewai_agent/run.py
deactivate
