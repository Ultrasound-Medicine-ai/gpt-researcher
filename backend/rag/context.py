"""Assemble chat context under a token budget with parent-merged children."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from rag.chunking import estimate_tokens
from rag.retrieve import RetrievedChunk


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return max(200, int(raw)) if raw else default
    except ValueError:
        return default


@dataclass
class Citation:
    chunk_id: str
    title: str
    page_number: Optional[int]
    source_url: str
    excerpt: str


@dataclass
class AssembledContext:
    evidence_block: str
    citations: list[Citation] = field(default_factory=list)
    recent_dialog: str = ""
    summary: str = ""
    total_tokens: int = 0
    rag_degraded: bool = False


def recent_dialog_text(messages: list[dict], *, max_turns: int = 6) -> str:
    if not messages:
        return ""
    # Keep last N user/assistant turns
    trimmed = messages[-(max_turns * 2) :]
    lines = []
    for m in trimmed:
        role = m.get("role") or "user"
        content = (m.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def session_summary_stub(messages: list[dict], *, max_chars: int = 800) -> str:
    """Lightweight summary placeholder (first user + last user intents)."""
    users = [
        (m.get("content") or "").strip()
        for m in messages
        if m.get("role") == "user" and (m.get("content") or "").strip()
    ]
    if not users:
        return ""
    if len(users) == 1:
        return users[0][:max_chars]
    return f"Initial: {users[0][:300]}\nLatest: {users[-1][:300]}"[:max_chars]


def _prefix_within_tokens(text: str, token_budget: int) -> str:
    text = text or ""
    if token_budget <= 0:
        return ""
    if estimate_tokens(text) <= token_budget:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if estimate_tokens(text[:mid]) <= token_budget:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip()


def _remove_exact_overlap(previous: str, current: str, *, min_chars: int = 8) -> str:
    """Remove the longest exact suffix/prefix overlap from current."""
    left = (previous or "").rstrip()
    right = (current or "").lstrip()
    max_chars = min(len(left), len(right))
    for size in range(max_chars, min_chars - 1, -1):
        if left[-size:] == right[:size]:
            return right[size:].lstrip()
    return right


def _continuous_child_groups(
    children: list[RetrievedChunk],
) -> list[list[RetrievedChunk]]:
    by_parent: dict[str, list[RetrievedChunk]] = {}
    for chunk in children:
        by_parent.setdefault(chunk.parent_id or chunk.chunk_id, []).append(chunk)

    runs: list[list[RetrievedChunk]] = []
    for family in by_parent.values():
        family.sort(
            key=lambda c: (
                c.child_index is None,
                c.child_index if c.child_index is not None else c.retrieval_rank,
                c.retrieval_rank,
            )
        )
        current: list[RetrievedChunk] = []
        for chunk in family:
            is_contiguous = bool(
                current
                and current[-1].child_index is not None
                and chunk.child_index is not None
                and chunk.child_index == current[-1].child_index + 1
            )
            if current and not is_contiguous:
                runs.append(current)
                current = []
            current.append(chunk)
        if current:
            runs.append(current)

    runs.sort(
        key=lambda group: (
            min(c.retrieval_priority for c in group),
            min(c.retrieval_rank for c in group),
            -max(c.score for c in group),
        )
    )
    return runs


def _render_evidence_group(
    group: list[RetrievedChunk],
) -> tuple[str, list[Citation]]:
    first = group[0]
    child_ids = ",".join(chunk.chunk_id for chunk in group)
    cite_line = (
        f"[chunk_id={first.chunk_id} child_ids={child_ids}"
        + (f" page={first.page_number}" if first.page_number is not None else "")
        + (f" url={first.source_url}" if first.source_url else "")
        + "]"
    )
    merged = first.content.strip()
    for chunk in group[1:]:
        remainder = _remove_exact_overlap(merged, chunk.content)
        if remainder:
            merged = f"{merged}\n\n{remainder}"
    block = f"{cite_line}\nTitle: {first.title}\n{merged}"
    citations = [
        Citation(
            chunk_id=chunk.chunk_id,
            title=chunk.title,
            page_number=chunk.page_number,
            source_url=chunk.source_url,
            excerpt=chunk.content[:240],
        )
        for chunk in group
    ]
    return block, citations


def assemble_evidence(
    children: list[RetrievedChunk],
    *,
    token_budget: Optional[int] = None,
) -> AssembledContext:
    """
    Merge children that share a parent; truncate to token budget.
    Evidence text embeds chunk_id / page / url for the model to cite.
    """
    budget = (
        max(1, token_budget)
        if token_budget is not None
        else _env_int("RAG_CONTEXT_TOKEN_BUDGET", 3500)
    )

    blocks: list[str] = []
    citations: list[Citation] = []
    for group in _continuous_child_groups(children):
        block, group_citations = _render_evidence_group(group)
        candidate = "\n\n---\n\n".join([*blocks, block])
        if estimate_tokens(candidate) <= budget:
            blocks.append(block)
            citations.extend(group_citations)
            continue
        if not blocks:
            truncated = _prefix_within_tokens(block, budget)
            if truncated:
                blocks = [truncated]
                citations = group_citations
        # Continue: a later, smaller evidence group may still fit.

    evidence_block = "\n\n---\n\n".join(blocks)
    return AssembledContext(
        evidence_block=evidence_block,
        citations=citations,
        total_tokens=estimate_tokens(evidence_block),
    )


def build_full_context(
    *,
    messages: list[dict],
    children: list[RetrievedChunk],
    base_context: str = "",
    rag_degraded: bool = False,
) -> AssembledContext:
    budget = _env_int("RAG_CONTEXT_TOKEN_BUDGET", 3500)
    recent = recent_dialog_text(messages)
    summary = session_summary_stub(messages)
    parts = []
    if summary:
        parts.append(f"Session summary:\n{summary}")
    if recent:
        parts.append(f"Recent dialogue:\n{recent}")
    if base_context.strip():
        # Keep base (report/sources) but budget-trim
        trimmed = base_context.strip()
        if estimate_tokens(trimmed) > _env_int("RAG_BASE_CONTEXT_TOKENS", 1500):
            trimmed = trimmed[:3000]
        parts.append(f"Session materials:\n{trimmed}")
    prefix = "\n\n".join(parts)
    evidence_heading = (
        "Retrieved evidence (cite chunk_id/page/url; if insufficient say you are uncertain):\n"
    )
    # Keep room for at least one evidence span when retrieval produced results.
    prefix_limit = max(0, budget - (200 if children else 0))
    prefix = _prefix_within_tokens(prefix, prefix_limit)
    evidence_overhead = estimate_tokens(
        f"{prefix}\n\n{evidence_heading}" if prefix else evidence_heading
    )
    evidence = assemble_evidence(
        children,
        token_budget=max(1, budget - evidence_overhead),
    )
    full_parts = [prefix] if prefix else []
    if evidence.evidence_block:
        full_parts.append(evidence_heading + evidence.evidence_block)
    full = "\n\n".join(full_parts)
    full = _prefix_within_tokens(full, budget)
    evidence.recent_dialog = recent
    evidence.summary = summary
    evidence.evidence_block = full
    evidence.total_tokens = estimate_tokens(full)
    evidence.rag_degraded = rag_degraded
    return evidence
