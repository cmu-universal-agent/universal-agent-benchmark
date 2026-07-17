#!/usr/bin/env python3
"""Validate local source caches used by the eight-task core pilot."""

from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _gzip_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    pubmed_path = DATA / "pubmedqa" / "ori_pqal.json"
    pubmed = _json(pubmed_path)
    _require(len(pubmed) == 1000, f"PubMedQA expected 1000, found {len(pubmed)}")
    _require(
        all({"QUESTION", "CONTEXTS", "final_decision"} <= set(row) for row in pubmed.values()),
        "PubMedQA required fields missing",
    )
    print("CACHE_OK PubMedQA records=1000")

    health_path = DATA / "healthbench" / "2025-05-07-06-14-12_oss_eval.jsonl"
    _require(health_path.stat().st_size == 60_258_154, "HealthBench size mismatch")
    digest = hashlib.md5(health_path.read_bytes()).digest()  # source-published Content-MD5
    _require(
        base64.b64encode(digest).decode() == "WG5ihzNmgj88RcJMS+YHuA==",
        "HealthBench MD5 mismatch",
    )
    health = _jsonl(health_path)
    _require(len(health) == 5000, f"HealthBench expected 5000, found {len(health)}")
    _require(
        all({"prompt_id", "prompt", "rubrics", "example_tags"} <= set(row) for row in health),
        "HealthBench required fields missing",
    )
    print("CACHE_OK HealthBench records=5000 bytes=60258154 md5=verified")

    aci_dir = DATA / "vendor" / "aci-bench" / "data" / "challenge_data"
    aci_expected = {
        "train.csv": 67,
        "valid.csv": 20,
        "clinicalnlp_taskB_test1.csv": 40,
        "clinicalnlp_taskC_test2.csv": 40,
        "clef_taskC_test3.csv": 40,
    }
    aci_total = 0
    for name, expected in aci_expected.items():
        rows = _csv(aci_dir / name)
        _require(len(rows) == expected, f"ACI-Bench {name}: {len(rows)}/{expected}")
        _require(
            all({"dataset", "encounter_id", "dialogue", "note"} <= set(row) for row in rows),
            f"ACI-Bench {name} required fields missing",
        )
        aci_total += len(rows)
    print(f"CACHE_OK ACI-Bench records={aci_total} splits=5")

    med_dir = DATA / "vendor" / "med-safety-bench" / "datasets" / "test" / "gpt4"
    med_total = 0
    for category in range(1, 10):
        rows = _csv(med_dir / f"med_safety_demonstrations_category_{category}.csv")
        _require(
            all({"harmful_medical_request", "safe_response"} <= set(row) for row in rows),
            f"MedSafetyBench category {category} required fields missing",
        )
        med_total += len(rows)
    _require(med_total == 450, f"MedSafetyBench gpt4 test expected 450, found {med_total}")
    print("CACHE_OK MedSafetyBench records=450 categories=9")

    amazon_dir = DATA / "amazon_reviews_2023"
    reviews = _gzip_jsonl(amazon_dir / "Subscription_Boxes.jsonl.gz")
    metadata = _gzip_jsonl(amazon_dir / "meta_Subscription_Boxes.jsonl.gz")
    _require(len(reviews) == 16_216, f"Amazon reviews expected 16216, found {len(reviews)}")
    _require(len(metadata) == 641, f"Amazon metadata expected 641, found {len(metadata)}")
    _require(
        all({"parent_asin", "rating", "timestamp"} <= set(row) for row in reviews),
        "Amazon review required fields missing",
    )
    print("CACHE_OK AmazonReviews2023 reviews=16216 metadata=641")

    tau_dir = DATA / "vendor" / "tau2-retail"
    tasks = _json(tau_dir / "tasks.json")
    splits = _json(tau_dir / "split_tasks.json")
    database = _json(tau_dir / "db.json")
    policy = (tau_dir / "policy.md").read_text(encoding="utf-8")
    _require(len(tasks) == 114, f"tau retail expected 114 tasks, found {len(tasks)}")
    _require(
        {key: len(value) for key, value in splits.items()} == {"train": 74, "test": 40, "base": 114},
        "tau retail split counts mismatch",
    )
    _require(set(database) == {"orders", "products", "users"}, "tau retail db collections mismatch")
    _require(bool(policy.strip()), "tau retail policy is empty")
    print("CACHE_OK tau2-retail tasks=114 train=74 test=40 db=verified")
    print("CORE_DATASET_CACHES_OK datasets=6 core_tasks=8")


if __name__ == "__main__":
    main()
