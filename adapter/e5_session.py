"""Pinned half-duplex user simulation for formal E5 runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

from adapter.schemas import BenchmarkTask

FIRST_AGENT_MESSAGE = "Hi! How can I help you today?"
STOP_MARKERS = ("###STOP###", "###TRANSFER###", "###OUT-OF-SCOPE###")
SIMULATOR_VERSION = "tau2-user-simulator@1d244f5"
SESSION_PROTOCOL_VERSION = "1.6"
SIMULATOR_MODEL = "gpt-4o-mini"
SIMULATOR_TEMPERATURE = 0
SIMULATOR_MAX_OUTPUT_TOKENS = 4096
E5_AGENT_SYSTEM_PROMPT = (
    "You are a retail customer-support agent. Use the provided tools to resolve "
    "the customer's issue. Follow policy and only use allowed tools. A tool "
    "response with ok=false means the action did not happen; do not claim that it "
    "did. Reply with exactly one JSON object matching the public E5 schema. "
    "Include schema_version='1.0', the task's case_id, task_id='E5', result, "
    "explanation, evidence_ids, confidence, and risk_or_uncertainty. The result "
    "must include resolution_status, customer_message, and final_state. "
    "The result.final_state object must report action_taken as refund, exchange, "
    "return, escalate, or no_action; when escalating it must also report the "
    "tool-call escalation_reason. Report only values directly supported by tool "
    "calls/results. Never invent ticket_id, order_status, or other unavailable "
    "business state. Authoritative final state is verified locally from the tool "
    "trace and replay evaluator."
)
SIMULATOR_GUIDELINES = """# User Simulation Guidelines
You are playing the role of a customer contacting a customer service representative.
Your goal is to simulate realistic customer interactions while following specific scenario instructions.
## Core Principles
- Generate one message at a time, maintaining natural conversation flow.
- Strictly follow the scenario instructions you have received.
- Never make up or hallucinate information not provided in the scenario instructions. Information that is not provided in the scenario instructions should be considered unknown or unavailable.
- Avoid repeating the exact instructions verbatim. Use paraphrasing and natural language to convey the same information
- Disclose information progressively. Wait for the agent to ask for specific information before providing it.
## Task Completion
- The goal is to continue the conversation until the task is complete.
- If the instruction goal is satisified, generate the '###STOP###' token to end the conversation.
- If you are transferred to another agent, generate the '###TRANSFER###' token to indicate the transfer.
- If you find yourself in a situation in which the scenario does not provide enough information for you to continue the conversation, generate the '###OUT-OF-SCOPE###' token to end the conversation.
Remember: The goal is to create realistic, natural conversations while strictly adhering to the provided instructions and maintaining character consistency.
"""


@dataclass
class E5SessionResult:
    final_output: str
    token_usage: dict[str, int | None]
    assistant_turns: list[str]
    simulator: dict[str, Any]


def _load_gold(task: BenchmarkTask) -> dict[str, Any]:
    path = os.getenv("BENCHMARK_E5_GOLD_PATH")
    if not path:
        raise RuntimeError("formal E5 requires BENCHMARK_E5_GOLD_PATH")
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["case_id"] == task.case_id:
                return row["gold"]
    raise RuntimeError(f"E5 gold is missing case {task.case_id}")


def _sum_usage(
    total: dict[str, int | None],
    value: dict[str, int | None],
) -> None:
    for key in total:
        if value.get(key) is not None:
            total[key] = (total[key] or 0) + int(value[key])


def _agent_prompt(task: BenchmarkTask, transcript: list[tuple[str, str]]) -> str:
    history = "\n\n".join(f"{role}: {content}" for role, content in transcript)
    return (
        f"Case ID: {task.case_id}\nTask ID: E5\n\n{task.prompt}\n\n"
        "Continue this customer-support conversation. Use tools when needed. "
        "Respond only to the latest customer message.\n\n"
        f"{history}"
    )


def run_e5_session(
    task: BenchmarkTask,
    run_agent_turn: Callable[
        [str], tuple[str, dict[str, int | None]]
    ],
) -> E5SessionResult:
    gold = _load_gold(task)
    user_simulator = gold.get("user_simulator")
    if not isinstance(user_simulator, dict):
        raise RuntimeError("formal E5 requires a user_simulator configuration")
    required_simulator_fields = ("seed", "task_instructions", "max_turns")
    missing_fields = [
        key for key in required_simulator_fields if key not in user_simulator
    ]
    if missing_fields:
        raise RuntimeError(
            "formal E5 user_simulator is missing required fields: "
            + ", ".join(missing_fields)
        )
    simulator = {
        key: user_simulator[key]
        for key in required_simulator_fields
    }
    instructions = str(simulator["task_instructions"]).strip()
    if (
        not instructions
        or instructions == "."
        or (instructions.startswith("<") and instructions.endswith(">"))
    ):
        raise RuntimeError("formal E5 requires non-placeholder task_instructions")
    simulator["task_instructions"] = instructions
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    system = (
        f"{SIMULATOR_GUIDELINES}\n<scenario>\n"
        f"{simulator['task_instructions']}\n</scenario>"
    )
    simulator_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": FIRST_AGENT_MESSAGE},
    ]
    transcript: list[tuple[str, str]] = [("Assistant", FIRST_AGENT_MESSAGE)]
    assistant_turns = [FIRST_AGENT_MESSAGE]
    agent_usage = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }
    simulator_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    final_output = FIRST_AGENT_MESSAGE

    for _ in range(int(simulator["max_turns"])):
        response = client.chat.completions.create(
            model=SIMULATOR_MODEL,
            messages=simulator_messages,
            temperature=SIMULATOR_TEMPERATURE,
            max_completion_tokens=SIMULATOR_MAX_OUTPUT_TOKENS,
            seed=int(simulator["seed"]),
        )
        user_message = response.choices[0].message.content or ""
        usage = response.usage
        if usage is not None:
            simulator_usage["input_tokens"] += usage.prompt_tokens or 0
            simulator_usage["output_tokens"] += usage.completion_tokens or 0
            simulator_usage["total_tokens"] += usage.total_tokens or 0
        simulator_messages.append({"role": "assistant", "content": user_message})
        if any(marker in user_message for marker in STOP_MARKERS):
            return E5SessionResult(
                final_output=final_output,
                token_usage=agent_usage,
                assistant_turns=assistant_turns,
                simulator={
                    "protocol_version": SESSION_PROTOCOL_VERSION,
                    "version": SIMULATOR_VERSION,
                    "model": SIMULATOR_MODEL,
                    "temperature": SIMULATOR_TEMPERATURE,
                    "max_output_tokens": SIMULATOR_MAX_OUTPUT_TOKENS,
                    "seed": simulator["seed"],
                    "turns": len(assistant_turns) - 1,
                    "token_usage": simulator_usage,
                    "termination": next(
                        marker for marker in STOP_MARKERS if marker in user_message
                    ),
                },
            )

        transcript.append(("Customer", user_message))
        final_output, turn_usage = run_agent_turn(_agent_prompt(task, transcript))
        _sum_usage(agent_usage, turn_usage)
        transcript.append(("Assistant", final_output))
        assistant_turns.append(final_output)
        simulator_messages.append({"role": "user", "content": final_output})

    raise RuntimeError("E5 user simulator reached max_turns")
