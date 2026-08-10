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


def assemble_evidence(
    children: list[RetrievedChunk],
    *,
    token_budget: Optional[int] = None,
) -> AssembledContext:
    """
    Merge children that share a parent; truncate to token budget.
    Evidence text embeds chunk_id / page / url for the model to cite.
    """
    budget = token_budget or _env_int("RAG_CONTEXT_TOKEN_BUDGET", 3500)
    # Group by parent (or self if no parent)
    groups: dict[str, list[RetrievedChunk]] = {}
    for ch in children:
        key = ch.parent_id or ch.chunk_id
        groups.setdefault(key, []).append(ch)

    # Preserve score order by best child in group
    ordered_keys = sorted(
        groups.keys(),
        key=lambda k: max(c.score for c in groups[k]),
        reverse=True,
    )

    blocks: list[str] = []
    citations: list[Citation] = []
    used = 0
    for key in ordered_keys:
        group = sorted(groups[key], key=lambda c: c.score, reverse=True)
        merged_parts = []
        group_citations: list[Citation] = []
        for ch in group:
            cite_line = (
                f"[chunk_id={ch.chunk_id}"
                + (f" page={ch.page_number}" if ch.page_number is not None else "")
                + (f" url={ch.source_url}" if ch.source_url else "")
                + "]"
            )
            part = f"{cite_line}\nTitle: {ch.title}\n{ch.content.strip()}"
            merged_parts.append(part)
            group_citations.append(
                Citation(
                    chunk_id=ch.chunk_id,
                    title=ch.title,
                    page_number=ch.page_number,
                    source_url=ch.source_url,
                    excerpt=ch.content[:240],
                )
            )
        block = "\n\n".join(merged_parts)
        cost = estimate_tokens(block)
        if used + cost > budget and blocks:
            break
        # If single block exceeds budget, truncate content
        if cost > budget and not blocks:
            # keep head of first child only
            ch = group[0]
            excerpt = ch.content[: max(200, budget * 2)]
            block = (
                f"[chunk_id={ch.chunk_id}"
                + (f" page={ch.page_number}" if ch.page_number is not None else "")
                + (f" url={ch.source_url}" if ch.source_url else "")
                + f"]\nTitle: {ch.title}\n{excerpt}"
            )
            citations = [
                Citation(
                    chunk_id=ch.chunk_id,
                    title=ch.title,
                    page_number=ch.page_number,
                    source_url=ch.source_url,
                    excerpt=excerpt[:240],
                )
            ]
            blocks = [block]
            used = estimate_tokens(block)
            break
        blocks.append(block)
        citations.extend(group_citations)
        used += cost

    return AssembledContext(
        evidence_block="\n\n---\n\n".join(blocks),
        citations=citations,
        total_tokens=used,
    )


def build_full_context(
    *,
    messages: list[dict],
    children: list[RetrievedChunk],
    base_context: str = "",
    rag_degraded: bool = False,
) -> AssembledContext:
    recent = recent_dialog_text(messages)
    summary = session_summary_stub(messages)
    evidence = assemble_evidence(children)
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
    if evidence.evidence_block:
        parts.append(
            "Retrieved evidence (cite chunk_id/page/url; if insufficient say you are uncertain):\n"
            + evidence.evidence_block
        )
    full = "\n\n".join(parts)
    evidence.recent_dialog = recent
    evidence.summary = summary
    evidence.evidence_block = full
    evidence.total_tokens = estimate_tokens(full)
    evidence.rag_degraded = rag_degraded
    return evidence
