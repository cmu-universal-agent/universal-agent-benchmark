#!/usr/bin/env python3
"""Build a small set of synthetic-benchmark medical_diagnostic tasks from PubMedQA.

PubMedQA (https://github.com/pubmedqa/pubmedqa) provides public biomedical
research-literature question answering data (PubMed abstracts + a yes/no/maybe
question), not real patient records or clinical cases. Only the small expert
labeled split (data/ori_pqal.json, 1k entries) is used here -- the much larger
artificial (~211k) and unlabeled (~61k) splits are intentionally not pulled in,
and only a handful of entries are sampled into benchmark tasks.
"""

import argparse
import json
import random
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "pubmedqa" / "ori_pqal.json"
OUTPUT_DIR = ROOT / "verticals" / "medical_diagnostic"
SOURCE_URL = (
    "https://raw.githubusercontent.com/pubmedqa/pubmedqa/master/data/ori_pqal.json"
)

PROMPT_TEMPLATE = """You are a medical evidence-review assistant for a benchmark test. \
This is a synthetic evaluation task derived from public biomedical research \
abstracts (PubMedQA) -- it is not a real patient case, and no real clinical \
decision should be made from your answer.

Read the following research abstract context, then answer the research \
question using only the evidence given. The context below already contains \
everything needed to answer -- a literature lookup tool may be available, \
but you should not need to call it.

Source PubMed ID: {pubmed_id}

Context:
{context}

Question: {question}

Instructions:
- Answer strictly based on the context above. Do not rely on outside medical \
knowledge as fact.
- If the context is ambiguous or insufficient for a confident answer, answer \
"maybe" and recommend that a qualified medical professional review the primary \
literature.
- Return exactly one JSON object with these keys: task_id, answer, rationale, \
confidence, safety_note.
  - task_id must be "{task_id}".
  - answer must be exactly one of: "yes", "no", "maybe".
  - rationale must be one to two sentences grounded in the context.
  - confidence must be one of: "low", "medium", "high".
  - safety_note must be exactly: "no real clinical decision made"."""


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        dest.write_bytes(response.read())


def _load_dataset(refresh: bool) -> dict:
    if refresh or not CACHE_PATH.exists():
        print(f"Downloading {SOURCE_URL} -> {CACHE_PATH}")
        _download(SOURCE_URL, CACHE_PATH)
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _sample_ids(dataset: dict, per_label: dict[str, int], seed: int) -> list[str]:
    # Each label gets its own independently-seeded shuffle, then a slice --
    # this way raising a label's count is always a superset of the previous
    # sample (rather than shifting a single shared RNG stream and silently
    # reassigning task_ids to different underlying entries).
    by_label: dict[str, list[str]] = {}
    for pmid, entry in dataset.items():
        by_label.setdefault(entry["final_decision"], []).append(pmid)

    chosen: list[str] = []
    for label, count in per_label.items():
        rng = random.Random(f"{seed}:{label}")
        pool = list(by_label.get(label, []))
        rng.shuffle(pool)
        chosen.extend(pool[:count])
    return chosen


def build_tasks(seed: int, refresh: bool) -> list[Path]:
    dataset = _load_dataset(refresh)
    per_label = {"yes": 4, "no": 4, "maybe": 2}
    pmids = _sample_ids(dataset, per_label, seed)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT_DIR.glob("task_*.json"):
        stale.unlink()

    written = []
    for i, pmid in enumerate(pmids, start=1):
        entry = dataset[pmid]
        task_id = f"MED-{i:03d}"
        context = " ".join(entry["CONTEXTS"])
        prompt = PROMPT_TEMPLATE.format(
            context=context, question=entry["QUESTION"], task_id=task_id, pubmed_id=pmid
        )

        task = {
            "task_id": task_id,
            "vertical": "medical_diagnostic",
            "prompt": prompt,
            "expected_output_type": "json",
            "metadata": {
                "source": "pubmedqa/ori_pqal.json",
                "pubmedqa_id": pmid,
                "ground_truth": entry["final_decision"],
            },
        }

        out_path = OUTPUT_DIR / f"task_{i:03d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(task, f, indent=2)
            f.write("\n")
        written.append(out_path)

    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download the dataset even if a local cache exists.",
    )
    args = parser.parse_args()

    written = build_tasks(seed=args.seed, refresh=args.refresh)
    for path in written:
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
