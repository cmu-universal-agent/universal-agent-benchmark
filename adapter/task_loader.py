"""Load legacy and Benchmark Case Schema v1.0 task files consistently.

Legacy task files remain supported while the team reviews the final v1.0
field mapping. New v1.0 files are converted into the runtime representation
used by all framework adapters without rewriting the source JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapter.schemas import BenchmarkTask


V1_TO_RUNTIME_VERTICAL = {
    "healthcare": "medical_diagnostic",
    "ecommerce": "ecommerce_trend_research",
    "smoke_test": "smoke_test",
}


def render_v1_prompt(
    input_value: dict[str, Any],
    *,
    case_id: str | None = None,
    task_id: str | None = None,
) -> str:
    """Render structured v1.0 input into a deterministic agent prompt."""
    sections = [str(input_value["instruction"]).strip()]

    if case_id and task_id:
        sections.append(
            "Benchmark identity:\n"
            + json.dumps(
                {"case_id": case_id, "task_id": task_id},
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    data = input_value.get("data", {})
    if data:
        sections.append(
            "Input data:\n" + json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        )

    source_documents = input_value.get("source_documents", [])
    if source_documents:
        rendered_documents = []
        for document in source_documents:
            heading = f"[{document['source_id']}]"
            if document.get("title"):
                heading += f" {document['title']}"
            rendered_documents.append(f"{heading}\n{document['content']}")
        sections.append("Source documents:\n" + "\n\n".join(rendered_documents))

    return "\n\n".join(sections)


def task_from_dict(data: dict[str, Any]) -> BenchmarkTask:
    """Convert a task dictionary from either supported format."""
    if data.get("schema_version") == "1.0":
        input_value = data["input"]
        schema_vertical = data["vertical"]
        runtime_vertical = V1_TO_RUNTIME_VERTICAL.get(schema_vertical, schema_vertical)
        metadata = dict(data.get("metadata", {}))
        metadata["schema_vertical"] = schema_vertical
        metadata["case_id"] = data["case_id"]

        return BenchmarkTask(
            task_id=data["task_id"],
            vertical=runtime_vertical,
            prompt=render_v1_prompt(
                input_value,
                case_id=data["case_id"],
                task_id=data["task_id"],
            ),
            expected_output_type="json",
            metadata=metadata,
            schema_version="1.0",
            case_id=data["case_id"],
            allowed_tools=(
                list(data["allowed_tools"])
                if data.get("allowed_tools") is not None
                else None
            ),
            stress_type=data["stress_type"],
            input_data=dict(input_value.get("data", {})),
        )

    return BenchmarkTask(
        task_id=data["task_id"],
        vertical=data["vertical"],
        prompt=data["prompt"],
        expected_output_type=data.get("expected_output_type", "json"),
        metadata=dict(data.get("metadata", {})),
        allowed_tools=(
            list(data["allowed_tools"])
            if data.get("allowed_tools") is not None
            else None
        ),
    )


def load_task(task_path: Path) -> BenchmarkTask:
    """Read a JSON task file and convert it to ``BenchmarkTask``."""
    with open(task_path, "r", encoding="utf-8") as file:
        return task_from_dict(json.load(file))
