#!/usr/bin/env python3
"""Build a small set of synthetic-benchmark ecommerce_trend_research tasks
from the Amazon Reviews 2023 dataset (McAuley Lab, UCSD:
https://cseweb.ucsd.edu/~jmcauley/datasets.html).

Only the smallest product category (Subscription_Boxes: ~16k reviews, 641
items) is pulled -- not the full 571M-review dataset. Reviews are aggregated
into per-product yearly review-count / average-rating series, and a handful
of products with a clear rising, declining, or stable trend are sampled into
benchmark tasks. This is historical review data, not a live market feed --
tasks make clear no real purchasing decision should be made from the answer.
"""

import argparse
import gzip
import json
import random
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "amazon_reviews_2023"
REVIEWS_CACHE = CACHE_DIR / "Subscription_Boxes.jsonl.gz"
META_CACHE = CACHE_DIR / "meta_Subscription_Boxes.jsonl.gz"
OUTPUT_DIR = ROOT / "verticals" / "ecommerce_trend_research"

REVIEWS_URL = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/"
    "review_categories/Subscription_Boxes.jsonl.gz"
)
META_URL = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/"
    "meta_categories/meta_Subscription_Boxes.jsonl.gz"
)

MIN_TOTAL_REVIEWS = 15
MIN_DISTINCT_YEARS = 3
RISING_RATIO = 1.5
DECLINING_RATIO = 1 / 1.5

PROMPT_TEMPLATE = """You are an e-commerce trend research assistant for a benchmark test. \
This is a synthetic evaluation task built from real, historical Amazon product \
review data (Amazon Reviews 2023, McAuley Lab, UCSD) -- it does not represent \
live or current market conditions, and no real purchasing or business decision \
should be made from your answer.

Product: "{title}" (category: Subscription Boxes)
Product ID: {parent_asin}

Yearly review activity for this product:
{year_table}

The data above already contains everything needed to answer -- a review-history \
lookup tool may be available, but you should not need to call it.

Based only on the data above, synthesize the trend for this product.

Instructions:
- Identify whether review volume is rising, declining, or stable across the \
years shown.
- Identify whether the average rating (sentiment) is improving, declining, or \
stable across the years shown.
- Do not invent data points that are not shown above.
- Return exactly one JSON object with these keys: task_id, trend_direction, \
sentiment_direction, trend_summary, confidence, safety_note.
  - task_id must be "{task_id}".
  - trend_direction must be exactly one of: "rising", "declining", "stable".
  - sentiment_direction must be exactly one of: "improving", "declining", "stable".
  - trend_summary must be one to two sentences grounded in the data above.
  - confidence must be one of: "low", "medium", "high".
  - safety_note must be exactly: "no real purchasing decision made"."""


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        dest.write_bytes(response.read())


def _load_jsonl_gz(path: Path, url: str, refresh: bool) -> list[dict]:
    if refresh or not path.exists():
        print(f"Downloading {url} -> {path}")
        _download(url, path)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _yearly_series(reviews: list[dict]) -> dict[str, dict[int, list[float]]]:
    by_product: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in reviews:
        year = datetime.fromtimestamp(r["timestamp"] / 1000, tz=timezone.utc).year
        by_product[r["parent_asin"]][year].append(r["rating"])
    return by_product


def _classify(year_counts: dict[int, int]) -> str:
    years = sorted(year_counts)
    first_half = years[: len(years) // 2] or years[:1]
    second_half = years[len(years) // 2 :]
    early_avg = sum(year_counts[y] for y in first_half) / len(first_half)
    late_avg = sum(year_counts[y] for y in second_half) / len(second_half)
    if early_avg == 0:
        return "rising" if late_avg > 0 else "stable"
    ratio = late_avg / early_avg
    if ratio >= RISING_RATIO:
        return "rising"
    if ratio <= DECLINING_RATIO:
        return "declining"
    return "stable"


def _classify_sentiment(year_avg_rating: dict[int, float]) -> str:
    years = sorted(year_avg_rating)
    if len(years) < 2:
        return "stable"
    delta = year_avg_rating[years[-1]] - year_avg_rating[years[0]]
    if delta >= 0.3:
        return "improving"
    if delta <= -0.3:
        return "declining"
    return "stable"


def _candidates(reviews: list[dict]) -> dict[str, dict]:
    by_product = _yearly_series(reviews)
    candidates = {}
    for parent_asin, year_ratings in by_product.items():
        total = sum(len(v) for v in year_ratings.values())
        if total < MIN_TOTAL_REVIEWS or len(year_ratings) < MIN_DISTINCT_YEARS:
            continue
        year_counts = {y: len(v) for y, v in year_ratings.items()}
        year_avg = {y: sum(v) / len(v) for y, v in year_ratings.items()}
        candidates[parent_asin] = {
            "year_counts": year_counts,
            "year_avg_rating": year_avg,
            "trend_direction": _classify(year_counts),
            "sentiment_direction": _classify_sentiment(year_avg),
        }
    return candidates


def _sample_asins(candidates: dict[str, dict], seed: int) -> list[str]:
    # Each trend bucket gets its own independently-seeded shuffle, then a
    # slice -- this way raising a bucket's count is always a superset of the
    # previous sample (rather than shifting a single shared RNG stream and
    # silently reassigning task_ids to different underlying products).
    by_trend: dict[str, list[str]] = defaultdict(list)
    for asin, info in candidates.items():
        by_trend[info["trend_direction"]].append(asin)

    per_trend = {"rising": 4, "declining": 4, "stable": 2}
    chosen = []
    for trend, count in per_trend.items():
        rng = random.Random(f"{seed}:{trend}")
        pool = list(by_trend.get(trend, []))
        rng.shuffle(pool)
        chosen.extend(pool[:count])
    return chosen


def build_tasks(seed: int, refresh: bool, overwrite: bool = False) -> list[Path]:
    existing = sorted(OUTPUT_DIR.glob("task_*.json"))
    if existing and not overwrite:
        raise FileExistsError(
            f"{len(existing)} task files already exist in {OUTPUT_DIR}. "
            "Use --overwrite only after backing them up or confirming replacement."
        )

    reviews = _load_jsonl_gz(REVIEWS_CACHE, REVIEWS_URL, refresh)
    meta_rows = _load_jsonl_gz(META_CACHE, META_URL, refresh)
    titles = {row["parent_asin"]: row.get("title", "Unknown product") for row in meta_rows}

    candidates = _candidates(reviews)
    asins = _sample_asins(candidates, seed)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in existing:
        stale.unlink()

    written = []
    for i, asin in enumerate(asins, start=1):
        info = candidates[asin]
        task_id = f"ECOM-{i:03d}"
        year_table = "\n".join(
            f"- {year}: {info['year_counts'][year]} reviews, "
            f"average rating {info['year_avg_rating'][year]:.1f}"
            for year in sorted(info["year_counts"])
        )
        title = titles.get(asin, "Unknown product")
        prompt = PROMPT_TEMPLATE.format(
            title=title, year_table=year_table, task_id=task_id, parent_asin=asin
        )

        task = {
            "task_id": task_id,
            "vertical": "ecommerce_trend_research",
            "prompt": prompt,
            "expected_output_type": "json",
            "metadata": {
                "source": "amazon_reviews_2023/Subscription_Boxes",
                "parent_asin": asin,
                "product_title": title,
                "ground_truth_trend_direction": info["trend_direction"],
                "ground_truth_sentiment_direction": info["sentiment_direction"],
                "yearly_data": {
                    str(y): {
                        "review_count": info["year_counts"][y],
                        "average_rating": round(info["year_avg_rating"][y], 2),
                    }
                    for y in sorted(info["year_counts"])
                },
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
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Download/read dataset caches without changing task files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace existing task_*.json files.",
    )
    args = parser.parse_args()

    if args.cache_only:
        reviews = _load_jsonl_gz(REVIEWS_CACHE, REVIEWS_URL, args.refresh)
        metadata = _load_jsonl_gz(META_CACHE, META_URL, args.refresh)
        print(
            f"cache ready: {CACHE_DIR.relative_to(ROOT)} "
            f"({len(reviews)} reviews, {len(metadata)} metadata rows)"
        )
        return

    written = build_tasks(
        seed=args.seed, refresh=args.refresh, overwrite=args.overwrite
    )
    for path in written:
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
