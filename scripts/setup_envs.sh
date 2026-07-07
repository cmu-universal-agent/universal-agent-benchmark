#!/bin/bash
set -e

echo "Creating OpenAI Agents SDK environment..."
python3 -m venv .venv-openai
source .venv-openai/bin/activate
pip install --upgrade pip
pip install -r frameworks/openai_agents_sdk/requirements.txt
deactivate

echo ""
echo "Creating LangGraph environment..."
python3 -m venv .venv-langgraph
source .venv-langgraph/bin/activate
pip install --upgrade pip
pip install -r frameworks/langgraph_agent/requirements.txt
deactivate

echo ""
echo "Creating CrewAI environment..."
python3 -m venv .venv-crewai
source .venv-crewai/bin/activate
pip install --upgrade pip
pip install -r frameworks/crewai_agent/requirements.txt
deactivate

echo ""
echo "All environments are ready."
