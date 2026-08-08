"""Retrieval / keyword scorers."""

from __future__ import annotations


def score_must_mention(report: str, keywords: list[str]) -> tuple[bool, list[str], dict[str, bool]]:
    lower = (report or "").lower()
    hits = {kw: kw.lower() in lower for kw in keywords}
    missing = [k for k, hit in hits.items() if not hit]
    failures = [f"missing keywords: {missing}"] if missing else []
    return len(failures) == 0, failures, hits
