#!/usr/bin/env python3
"""Validate task JSON files and report legacy versus Schema v1.0 status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.task_loader import load_task

SCHEMA_PATH = ROOT / "schemas" / "benchmark_case.schema.json"


def _task_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.rglob("task_*.json"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        type=Path,
        default=ROOT / "verticals",
        help="One task JSON file or a directory. Default: verticals/",
    )
    parser.add_argument(
        "--require-v1",
        action="store_true",
        help="Return a failure when any legacy task is found.",
    )
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit(
            "jsonschema is required. Run this with the CrewAI environment: "
            r".venv-crewai\Scripts\python.exe scripts\validate_tasks.py"
        ) from exc

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )

    paths = _task_paths(args.task)
    v1_count = 0
    legacy_count = 0
    invalid_count = 0

    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            invalid_count += 1
            print(f"INVALID {path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
            continue

        if raw.get("schema_version") != "1.0":
            try:
                load_task(path)
            except Exception as exc:
                invalid_count += 1
                print(
                    f"INVALID {path.relative_to(ROOT)}: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                legacy_count += 1
                print(f"LEGACY  {path.relative_to(ROOT)}")
            continue

        errors = sorted(validator.iter_errors(raw), key=lambda error: list(error.path))
        if errors:
            invalid_count += 1
            for error in errors:
                location = ".".join(str(part) for part in error.path) or "<root>"
                print(f"INVALID {path.relative_to(ROOT)} [{location}]: {error.message}")
        else:
            try:
                load_task(path)
            except Exception as exc:
                invalid_count += 1
                print(
                    f"INVALID {path.relative_to(ROOT)}: runtime conversion failed: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                v1_count += 1
                print(f"V1 PASS {path.relative_to(ROOT)}")

    print(
        f"\nfiles={len(paths)} v1_valid={v1_count} "
        f"legacy_compatible={legacy_count} invalid={invalid_count}"
    )
    if invalid_count or (args.require_v1 and legacy_count):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
