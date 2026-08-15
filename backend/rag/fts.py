"""Lightweight lexical preparation for PostgreSQL ``simple`` FTS."""

from __future__ import annotations

import re

import jieba

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*|\d+(?:\.\d+)?%?|[\u4e00-\u9fff]+")
_STOPWORDS = {
    "\u4e3a\u4ec0\u4e48", "\u5982\u4f55", "\u4ec0\u4e48", "\u600e\u6837", "\u5206\u522b", "\u54ea\u4e9b",
    "\u662f\u5426", "\u53ef\u4ee5", "\u9700\u8981", "\u8bf7", "\u65f6", "\u53ca", "\u548c", "\u7684", "\u4e86",
    "\u5417", "\u5462", "\u5404", "\u5728", "\u4e0e", "\u5e76", "\u53c8",
}
_TECHNICAL_TERMS = {
    "redlock", "lua", "fastapi", "hpa", "vpa", "sse", "ping",
    "traceroute", "iperf", "ttl", "rtt", "nx", "px", "requestid",
    "leasetime", "last-event-id",
}


def fts_terms(text: str, *, deduplicate: bool = True) -> list[str]:
    """Return stable Chinese/English lexical terms without extra NLP models."""
    terms: list[str] = []
    seen: set[str] = set()
    for piece in _TOKEN_RE.findall(text or ""):
        tokens = list(jieba.cut(piece, HMM=False)) if re.search(r"[\u4e00-\u9fff]", piece) else [piece]
        for token in tokens:
            value = token.strip().lower()
            if not value or value in _STOPWORDS or (deduplicate and value in seen):
                continue
            if deduplicate:
                seen.add(value)
            terms.append(value)
    return terms


def fts_index_text(*parts: str) -> str:
    """Prepare index text with useful frequency but no keyword-stuffing boost."""
    terms = fts_terms(" ".join(part or "" for part in parts), deduplicate=False)
    counts: dict[str, int] = {}
    capped: list[str] = []
    for term in terms:
        count = counts.get(term, 0)
        if count >= 3:
            continue
        counts[term] = count + 1
        capped.append(term)
    return " ".join(capped)


def fts_or_query(text: str) -> str:
    """Build an OR tsquery input from unique lexical terms."""
    return " | ".join(fts_terms(text))


def fts_anchor_terms(text: str) -> list[str]:
    """Return deterministic technical anchors used only to improve ordering."""
    raw_ascii = re.findall(r"[A-Za-z][A-Za-z0-9_.-]*|\d+(?:\.\d+)?%?", text or "")
    anchors: list[str] = []
    for raw in raw_ascii:
        value = raw.lower()
        is_structured = (
            any(ch.isdigit() for ch in raw)
            or "-" in raw
            or "_" in raw
            or (len(raw) > 1 and raw.isupper())
            or value in _TECHNICAL_TERMS
        )
        if is_structured and value not in anchors:
            anchors.append(value)
    return anchors
