"""
Deterministic citation injection.

Quality invariant:
- Only runs for numbered citation style after the report is already generated.
- On any failure, returns the original report unchanged (plus existing
  normalize_numbered_report path remains the caller fallback).
- Never modifies LLM generation parameters — post-process only.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？.!?])\s+|\n+")
_EXISTING_CITE = re.compile(r"\[(\d+)\]")


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]
    return parts


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def inject_deterministic_citations(
    report_markdown: str,
    registry,
    *,
    embeddings: Any | None = None,
    threshold: float = 0.42,
    max_cites_per_sentence: int = 2,
) -> str:
    """
    Attach [n] markers to body sentences by embedding similarity to sources.

    If embeddings are unavailable or matching fails, returns report_markdown
    unchanged so quality/generation is unaffected.
    """
    if not report_markdown or registry is None or not getattr(registry, "entries", None):
        return report_markdown

    try:
        # Split body vs references heading if present
        body = report_markdown
        refs_tail = ""
        for marker in ("\n## 参考文献", "\n## References"):
            idx = body.find(marker)
            if idx >= 0:
                refs_tail = body[idx:]
                body = body[:idx]
                break

        if embeddings is None:
            try:
                from gpt_researcher.config.config import Config
                from gpt_researcher.memory import Memory

                cfg = Config()
                embeddings = Memory(
                    cfg.embedding_provider,
                    cfg.embedding_model,
                    **cfg.embedding_kwargs,
                ).get_embeddings()
            except Exception as exc:
                logger.warning("Embeddings unavailable for cite inject: %s", exc)
                return report_markdown

        source_texts: list[str] = []
        for entry in registry.entries:
            title = entry.get("title") or ""
            raw = entry.get("raw_content") or ""
            source_texts.append(f"{title}\n{raw}"[:2000])

        # Prefer batch embed; fall back to per-item
        try:
            source_vecs = embeddings.embed_documents(source_texts)
        except Exception:
            source_vecs = [embeddings.embed_query(t) for t in source_texts]

        sentences = _split_sentences(body)
        if not sentences:
            return report_markdown

        try:
            sent_vecs = embeddings.embed_documents(sentences)
        except Exception:
            sent_vecs = [embeddings.embed_query(s) for s in sentences]

        rewritten: list[str] = []
        cited_indexes: set[int] = set()

        for sentence, svec in zip(sentences, sent_vecs):
            # Keep existing citations if model already produced valid ones
            existing = {int(n) for n in _EXISTING_CITE.findall(sentence)}
            valid_existing = {n for n in existing if 1 <= n <= len(registry.entries)}
            if valid_existing:
                cited_indexes.update(valid_existing)
                rewritten.append(sentence)
                continue

            scores = [
                (_cosine(svec, source_vecs[i]), i + 1)
                for i in range(len(source_vecs))
            ]
            scores.sort(reverse=True)
            picks = [idx for score, idx in scores if score >= threshold][:max_cites_per_sentence]
            if not picks and scores and scores[0][0] >= threshold * 0.85:
                # Soft fallback: take top-1 if reasonably close
                picks = [scores[0][1]]

            if picks:
                cited_indexes.update(picks)
                cite_str = "".join(f"[{n}]" for n in picks)
                # Avoid double-spacing before citation
                if sentence.endswith((".", "。", "!", "！", "?", "？")):
                    rewritten.append(f"{sentence[:-1]}{cite_str}{sentence[-1]}")
                else:
                    rewritten.append(f"{sentence}{cite_str}")
            else:
                rewritten.append(sentence)

        new_body = "\n\n".join(rewritten).strip()

        # Rebuild registry order: only cited sources, renumber 1..K if any cites
        if cited_indexes:
            from gpt_researcher.actions.citation_registry import SourceRegistry
            from gpt_researcher.actions.markdown_processing import (
                strip_apa_inline_citations,
                strip_existing_references_section,
                add_numbered_references,
            )

            ordered_old = sorted(cited_indexes)
            remap = {old: new for new, old in enumerate(ordered_old, start=1)}
            remapped_body = new_body
            # Replace higher numbers first to avoid collisions
            for old in sorted(ordered_old, reverse=True):
                remapped_body = remapped_body.replace(f"[{old}]", f"[__TMP_{remap[old]}__]")
            for new in remap.values():
                remapped_body = remapped_body.replace(f"[__TMP_{new}__]", f"[{new}]")

            new_entries = [registry.entries[old - 1] for old in ordered_old]
            new_registry = SourceRegistry(new_entries)
            cleaned = strip_apa_inline_citations(remapped_body)
            cleaned = strip_existing_references_section(cleaned)
            # Prefer original heading language from refs_tail if present
            heading = None
            if "参考文献" in refs_tail:
                heading = "## 参考文献"
            elif "References" in refs_tail:
                heading = "## References"
            return add_numbered_references(cleaned, new_registry, references_heading=heading)

        return report_markdown
    except Exception as exc:
        logger.warning("Deterministic citation inject failed (report unchanged): %s", exc)
        return report_markdown
