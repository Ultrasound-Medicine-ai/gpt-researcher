"""Parent/child chunking for hybrid RAG.

Parent ≈ section/chapter context; Child ≈ 300–600 tokens citeable span
with a small sliding overlap to preserve boundary context.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional


def estimate_tokens(text: str) -> int:
    """Rough token estimate: CJK ≈ 1 char/token, Latin ≈ word*1.3."""
    if not text:
        return 0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    other = max(0, len(text) - cjk)
    return max(1, cjk + int(latin_words * 1.3) + other // 8)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return max(1, int(raw)) if raw else default
    except ValueError:
        return default


def _env_nonnegative_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return max(0, int(raw)) if raw else default
    except ValueError:
        return default


def child_token_range() -> tuple[int, int]:
    lo = _env_int("RAG_CHILD_TOKENS_MIN", 300)
    hi = _env_int("RAG_CHILD_TOKENS_MAX", 600)
    if hi < lo:
        hi = lo
    return lo, hi


def child_overlap_tokens() -> int:
    return _env_nonnegative_int("RAG_CHILD_OVERLAP_TOKENS", 80)


def parent_max_tokens() -> int:
    return _env_int("RAG_PARENT_MAX_TOKENS", 1800)


@dataclass
class ChunkDraft:
    chunk_level: str  # parent|child
    content: str
    title: str = ""
    page_number: Optional[int] = None
    source_url: str = ""
    token_estimate: int = 0
    parent_index: Optional[int] = None  # for children → parent draft index
    metadata: dict[str, Any] = field(default_factory=dict)


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown-ish text into (title, body) sections."""
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?m)^(#{1,3}\s+.+)$", text)
    if len(parts) == 1:
        return [("", text)]
    sections: list[tuple[str, str]] = []
    # parts: [pre, heading, body, heading, body, ...]
    pre = parts[0].strip()
    if pre:
        sections.append(("", pre))
    i = 1
    while i < len(parts):
        heading = parts[i].lstrip("#").strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append((heading, body or heading))
        i += 2
    return sections or [("", text)]


def _window_chunks(text: str, *, min_tok: int, max_tok: int) -> list[str]:
    """Greedy windows targeting [min_tok, max_tok]."""
    text = (text or "").strip()
    if not text:
        return []
    # Prefer paragraph boundaries
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        paras = [text]
    windows: list[str] = []
    buf: list[str] = []
    buf_tok = 0
    for para in paras:
        pt = estimate_tokens(para)
        if pt > max_tok:
            if buf:
                windows.append("\n\n".join(buf))
                buf, buf_tok = [], 0
            # hard split long paragraph by chars ≈ tokens
            step = max(80, max_tok * 2)
            for i in range(0, len(para), step):
                piece = para[i : i + step].strip()
                if piece:
                    windows.append(piece)
            continue
        if buf_tok + pt > max_tok and buf_tok >= min_tok:
            windows.append("\n\n".join(buf))
            buf, buf_tok = [para], pt
        else:
            buf.append(para)
            buf_tok += pt
    if buf:
        windows.append("\n\n".join(buf))
    return windows


def _tail_within_tokens(text: str, token_budget: int) -> str:
    """Return the largest suffix that fits the approximate token budget."""
    text = (text or "").strip()
    if not text or token_budget <= 0:
        return ""
    if estimate_tokens(text) <= token_budget:
        return text

    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        if estimate_tokens(text[mid:]) <= token_budget:
            hi = mid
        else:
            lo = mid + 1
    suffix = text[lo:].strip()

    # Avoid starting in the middle of a Latin word when possible.
    if (
        lo > 0
        and lo < len(text)
        and re.match(r"[A-Za-z0-9_]", text[lo - 1])
        and re.match(r"[A-Za-z0-9_]", text[lo])
    ):
        boundary = re.search(r"[\s,.;:!?\u3002\uff0c\uff1b\uff1a\uff01\uff1f]", suffix)
        if boundary and boundary.end() < len(suffix):
            suffix = suffix[boundary.end() :].lstrip()
    return suffix


def _add_sliding_overlap(windows: list[str], overlap_tokens: int) -> list[str]:
    if overlap_tokens <= 0 or len(windows) < 2:
        return windows
    overlapped = [windows[0]]
    for previous, current in zip(windows, windows[1:]):
        tail = _tail_within_tokens(previous, overlap_tokens)
        overlapped.append(f"{tail}\n\n{current}" if tail else current)
    return overlapped


def build_parent_child_chunks(
    text: str,
    *,
    title: str = "",
    source_url: str = "",
    page_number: Optional[int] = None,
    extra_meta: Optional[dict] = None,
) -> list[ChunkDraft]:
    """Build parent section chunks + child citeable spans."""
    min_tok, max_tok = child_token_range()
    overlap_tok = min(child_overlap_tokens(), max(0, max_tok - 1))
    pmax = parent_max_tokens()
    drafts: list[ChunkDraft] = []
    meta = dict(extra_meta or {})

    for sec_title, body in _split_sections(text):
        section_title = sec_title or title or ""
        # Parent may need further split if huge
        parent_bodies = _window_chunks(body, min_tok=pmax // 2, max_tok=pmax) or [body]
        for parent_body in parent_bodies:
            parent_idx = len(drafts)
            drafts.append(
                ChunkDraft(
                    chunk_level="parent",
                    content=parent_body,
                    title=section_title,
                    page_number=page_number,
                    source_url=source_url,
                    token_estimate=estimate_tokens(parent_body),
                    metadata={**meta, "role": "parent"},
                )
            )
            # Reserve space for overlap so child chunks remain near max_tok.
            child_windows = _window_chunks(
                parent_body,
                min_tok=min_tok,
                max_tok=max(min_tok, max_tok - overlap_tok),
            )
            for child_index, child in enumerate(
                _add_sliding_overlap(child_windows, overlap_tok)
            ):
                drafts.append(
                    ChunkDraft(
                        chunk_level="child",
                        content=child,
                        title=section_title,
                        page_number=page_number,
                        source_url=source_url,
                        token_estimate=estimate_tokens(child),
                        parent_index=parent_idx,
                        metadata={
                            **meta,
                            "role": "child",
                            "overlap_tokens": overlap_tok,
                            "child_index": child_index,
                        },
                    )
                )
    return drafts


def content_checksum(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:64]
