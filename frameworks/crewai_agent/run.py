import json
import os
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM


ROOT = Path(__file__).resolve().parents[2]
TASK_PATH = ROOT / "verticals" / "smoke_test" / "task_001.json"

load_dotenv(ROOT / ".env", override=True)


def main():
    with open(TASK_PATH, "r", encoding="utf-8") as f:
        task_data = json.load(f)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4")

    # CrewAI often expects OpenAI models in this form:
    # openai/gpt-4, openai/gpt-4o-mini, etc.
    crewai_model_name = model_name if "/" in model_name else f"openai/{model_name}"

    llm = LLM(
        model=crewai_model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
    )

    agent = Agent(
        role="Benchmark Smoke Test Agent",
        goal="Return a clean structured JSON response for a framework benchmark.",
        backstory=(
            "You are used only for testing whether CrewAI can run the same "
            "standardized benchmark task as LangGraph and OpenAI Agents SDK."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description=task_data["prompt"],
        expected_output=(
            "Exactly one JSON object with keys: task_id, answer, safety_note. "
            "No markdown. No extra text."
        ),
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    print("\n=== CrewAI Result ===")
    print(result)


if __name__ == "__main__":
    main()
