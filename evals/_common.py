"""Shared helpers for Project-2 cheap eval runners. :-)"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence, TypeVar

DEFAULT_EVAL_SAMPLE_SEED = 42
T = TypeVar("T")


def resolve_sample_seed(cli_seed: int | None = None) -> int:
    """CLI --seed wins, then EVAL_SAMPLE_SEED, else default 42. :-)"""
    if cli_seed is not None:
        return int(cli_seed)
    raw = (os.getenv("EVAL_SAMPLE_SEED") or "").strip()
    if raw:
        return int(raw)
    return DEFAULT_EVAL_SAMPLE_SEED


def seeded_sample(population: Sequence[T], k: int, *, seed: int) -> list[T]:
    """Deterministic random.sample for reproducible eval subsets. :-)"""
    items = list(population)
    if k >= len(items):
        return items
    return random.Random(int(seed)).sample(items, k)


def seeded_stratified_sample(
    population: Sequence[T],
    k: int,
    *,
    key_fn,
    seed: int,
) -> tuple[list[T], dict[str, int]]:
    """Proportional stratified sample without replacement (seeded).

    1) Group by key_fn(item)
    2) Allocate quotas proportional to stratum size (largest-remainder)
    3) Sample within each stratum with Random(seed)
    4) If a stratum is short, redistribute remainder to largest remaining pools
    5) Shuffle final list with the same RNG

    Returns (sample, strata_counts). :-)
    """
    items = list(population)
    if k <= 0:
        return [], {}
    if k >= len(items):
        counts: dict[str, int] = {}
        for it in items:
            key = str(key_fn(it) or "Unknown")
            counts[key] = counts.get(key, 0) + 1
        return items, counts

    buckets: dict[str, list[T]] = {}
    for it in items:
        key = str(key_fn(it) or "Unknown")
        buckets.setdefault(key, []).append(it)

    n = len(items)
    # Largest-remainder quotas. :-)
    raw = {key: (len(bucket) / n) * k for key, bucket in buckets.items()}
    quotas = {key: int(v) for key, v in raw.items()}
    rem = k - sum(quotas.values())
    frac_order = sorted(raw.keys(), key=lambda key: (raw[key] - quotas[key], key), reverse=True)
    for key in frac_order:
        if rem <= 0:
            break
        quotas[key] += 1
        rem -= 1

    rng = random.Random(int(seed))
    picked: list[T] = []
    strata_counts: dict[str, int] = {}
    leftover_need = 0
    remaining_pools: dict[str, list[T]] = {}

    for key, bucket in buckets.items():
        q = min(quotas.get(key, 0), len(bucket))
        if q > 0:
            chosen = rng.sample(bucket, q)
            picked.extend(chosen)
            strata_counts[key] = q
            chosen_ids = {id(x) for x in chosen}
            leftover = [x for x in bucket if id(x) not in chosen_ids]
        else:
            leftover = list(bucket)
            strata_counts[key] = 0
        if leftover:
            remaining_pools[key] = leftover
        shortfall = quotas.get(key, 0) - q
        if shortfall > 0:
            leftover_need += shortfall

    # Redistribute shortfall from largest remaining pools. :-)
    while leftover_need > 0 and remaining_pools:
        key = max(remaining_pools.keys(), key=lambda kk: (len(remaining_pools[kk]), kk))
        pool = remaining_pools[key]
        idx = rng.randrange(len(pool))
        take = pool.pop(idx)
        picked.append(take)
        strata_counts[key] = strata_counts.get(key, 0) + 1
        leftover_need -= 1
        if not pool:
            del remaining_pools[key]

    rng.shuffle(picked)
    # Drop zero strata from report for clarity. :-)
    strata_counts = {k: v for k, v in sorted(strata_counts.items()) if v > 0}
    return picked[:k], strata_counts


def load_jsonl(
    path: Path,
    *,
    suite: str = "cheap",
    only_id: Optional[str] = None,
    include_blocked: bool = False,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if only_id and case.get("id") != only_id:
                continue
            status = (case.get("status") or "active").lower()
            if status == "blocked" and not include_blocked:
                continue
            case_suite = case.get("suite") or "cheap"
            if suite == "cheap" and case_suite not in ("cheap", "both"):
                continue
            if suite in ("full", "nightly") and case_suite == "cheap":
                # cheap-only cases still allowed under both; pure cheap skipped in full
                if case_suite != "both":
                    continue
            cases.append(case)
    return cases


def summarize(
    results: Iterable[dict[str, Any]],
    *,
    pillar: str,
    suite: str,
) -> dict[str, Any]:
    rows = list(results)
    passed = sum(1 for r in rows if r.get("passed"))
    failed = sum(1 for r in rows if r.get("passed") is False)
    skipped = sum(1 for r in rows if r.get("skipped"))
    return {
        "pillar": pillar,
        "suite": suite,
        "total": len(rows),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "ok": failed == 0,
        "results": rows,
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(
        f"[{summary['pillar']}/{summary['suite']}] "
        f"passed={summary['passed']} failed={summary['failed']} "
        f"skipped={summary.get('skipped', 0)} total={summary['total']}"
    )
    for row in summary.get("results") or []:
        if row.get("skipped"):
            print(f"  SKIP {row.get('id')}: {row.get('reason') or 'blocked'}")
            continue
        mark = "PASS" if row.get("passed") else "FAIL"
        fails = row.get("failures") or []
        extra = f" — {'; '.join(fails)}" if fails else ""
        print(f"  {mark} {row.get('id')}{extra}")
