"""Framework-neutral helpers for dataset mappings and deterministic splits."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from typing import Any, Iterable


SPLIT_RATIOS = {
    "development": 0.60,
    "pilot": 0.15,
    "validation": 0.15,
    "test": 0.10,
}


def validate_label_mapping(
    mapping_document: dict[str, Any],
    source_labels: Iterable[str],
    *,
    require_approved: bool = True,
) -> list[str]:
    """Return mapping coverage/target errors without changing source data."""
    errors: list[str] = []
    if require_approved and mapping_document.get("status") != "approved":
        errors.append("mapping status must be approved")

    target_values = set(mapping_document.get("target_values", []))
    mapping = mapping_document.get("mapping", {})
    if not isinstance(mapping, dict):
        return [*errors, "mapping must be an object"]

    invalid_targets = sorted(set(mapping.values()) - target_values)
    if invalid_targets:
        errors.append(f"mapping contains invalid target values: {invalid_targets}")

    observed = {str(label) for label in source_labels}
    unmapped = sorted(observed - set(mapping))
    if unmapped:
        errors.append(f"unmapped source labels: {unmapped}")
    return errors


def _group_counts(size: int) -> dict[str, int]:
    """Allocate one stratum with largest-remainder rounding."""
    raw = {name: size * ratio for name, ratio in SPLIT_RATIOS.items()}
    counts = {name: math.floor(value) for name, value in raw.items()}
    remaining = size - sum(counts.values())
    order = sorted(
        SPLIT_RATIOS,
        key=lambda name: (raw[name] - counts[name], SPLIT_RATIOS[name]),
        reverse=True,
    )
    for name in order[:remaining]:
        counts[name] += 1
    return counts


def build_split_manifest(
    records: Iterable[dict[str, Any]],
    *,
    seed: str = "uab-v1",
) -> list[dict[str, Any]]:
    """Create deterministic task/difficulty-stratified benchmark splits.

    Every record must provide `source_record_id`, `task_id`, and `difficulty`.
    `source_split` is copied as provenance when present. No source record is
    mutated.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for record in records:
        source_id = str(record["source_record_id"])
        if source_id in seen_ids:
            raise ValueError(f"duplicate source_record_id: {source_id}")
        seen_ids.add(source_id)
        key = (str(record["task_id"]), str(record["difficulty"]))
        groups[key].append(dict(record))

    manifest: list[dict[str, Any]] = []
    for (task_id, difficulty), group in sorted(groups.items()):
        ordered = sorted(
            group,
            key=lambda record: hashlib.sha256(
                f"{seed}|{task_id}|{difficulty}|{record['source_record_id']}".encode(
                    "utf-8"
                )
            ).hexdigest(),
        )
        counts = _group_counts(len(ordered))
        cursor = 0
        for split, count in counts.items():
            for record in ordered[cursor : cursor + count]:
                row = {
                    "source_record_id": str(record["source_record_id"]),
                    "task_id": task_id,
                    "difficulty": difficulty,
                    "split": split,
                }
                if record.get("source_split") is not None:
                    row["source_split"] = record["source_split"]
                manifest.append(row)
            cursor += count
    return sorted(manifest, key=lambda row: row["source_record_id"])
