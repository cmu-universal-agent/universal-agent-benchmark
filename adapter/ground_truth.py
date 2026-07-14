"""Ground-truth loading for verticals that have it (medical, ecommerce).

Shared by the report scripts so the vertical -> (metadata key, answer key)
mapping and the "read all task_*.json in a vertical dir" logic live in one
place instead of being copy-pasted across scripts/report_*.py.
"""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

GROUND_TRUTH_CONFIG = {
    "medical_diagnostic": {"metadata_key": "ground_truth", "answer_key": "answer"},
    "ecommerce_trend_research": {
        "metadata_key": "ground_truth_trend_direction",
        "answer_key": "trend_direction",
    },
}


def task_ids(vertical: str) -> set[str]:
    return {
        json.loads(p.read_text())["task_id"]
        for p in sorted((ROOT / "verticals" / vertical).glob("task_*.json"))
    }


def load_ground_truth(vertical: str) -> dict[str, Any]:
    config = GROUND_TRUTH_CONFIG[vertical]
    ground_truth = {}
    for task_path in sorted((ROOT / "verticals" / vertical).glob("task_*.json")):
        data = json.loads(task_path.read_text())
        ground_truth[data["task_id"]] = data["metadata"][config["metadata_key"]]
    return ground_truth
