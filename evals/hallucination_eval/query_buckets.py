"""Heuristic risk buckets for hallucination queries. :-)"""

from __future__ import annotations

import re

BUCKETS = (
    "pricing_compare",
    "fresh_news",
    "landscape_vendor",
    "howto_technical",
    "other",
)

_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "pricing_compare",
        re.compile(
            r"\b(pricing|price|compare|comparison|vs\.?|versus|cost|costs)\b",
            re.I,
        ),
    ),
    (
        "fresh_news",
        re.compile(
            r"\b(2025|2026|keynote|GTC|I/O|announcements?|live coverage|recaps?|"
            r"this year|latest news)\b",
            re.I,
        ),
    ),
    (
        "landscape_vendor",
        re.compile(
            r"\b(leading|vendors?|startups?|companies|landscape|ecosystem|"
            r"who are|which companies)\b",
            re.I,
        ),
    ),
    (
        "howto_technical",
        re.compile(
            r"\b(how|explain|techniques?|methods?|RAG|fine-?tun|benchmarks?|"
            r"evaluate|guardrail|aligning|quantization|context retention)\b",
            re.I,
        ),
    ),
]


def risk_bucket(query: str) -> str:
    text = query or ""
    for name, pattern in _RULES:
        if pattern.search(text):
            return name
    return "other"


def summarize_by_bucket(results: list[dict]) -> dict[str, dict]:
    """Aggregate MAJOR hallucination rates per risk_bucket. :-)"""
    buckets: dict[str, dict] = {}
    for row in results:
        q = row.get("input") or row.get("query") or ""
        bucket = row.get("risk_bucket") or risk_bucket(str(q))
        slot = buckets.setdefault(
            bucket,
            {"n": 0, "evaluated": 0, "major": 0, "hallucinated": 0},
        )
        slot["n"] += 1
        if row.get("error"):
            continue
        if row.get("is_hallucination") is not None:
            slot["evaluated"] += 1
            if row.get("is_hallucination"):
                slot["hallucinated"] += 1
        sev = (row.get("severity") or "").upper()
        if sev == "MAJOR":
            slot["major"] += 1
    out: dict[str, dict] = {}
    for name, slot in sorted(buckets.items()):
        evaluated = slot["evaluated"]
        out[name] = {
            "n": slot["n"],
            "evaluated": evaluated,
            "major": slot["major"],
            "hallucinated": slot["hallucinated"],
            "major_rate": (slot["major"] / evaluated) if evaluated else None,
            "hallucination_rate": (
                (slot["hallucinated"] / evaluated) if evaluated else None
            ),
        }
    return out
