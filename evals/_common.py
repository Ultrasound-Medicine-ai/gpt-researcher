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
