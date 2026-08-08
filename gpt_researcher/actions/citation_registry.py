"""Numbered citation registry for research reports."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    """Extract hostname from a URL without www prefix."""
    try:
        netloc = urlparse(url).netloc
        return netloc.replace("www.", "") or "unknown"
    except Exception:
        return "unknown"


def _count_cjk(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def maybe_repair_mojibake(text: str) -> str:
    """Cheap Latin-1/UTF-8 mojibake repair when Chinese was decoded wrongly.

    Only applies when the text has almost no CJK but latin-1→utf-8 yields more.
    """
    if not text or _count_cjk(text) >= 3:
        return text
    if not any(ch in text for ch in ("Ã", "Â", "ç", "ä", "å", "é", "è", "ï")):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if _count_cjk(repaired) > _count_cjk(text):
        return repaired
    return text


def extract_snippet(raw_content: str, max_len: int = 280) -> str:
    """Extract a readable text snippet from raw HTML or plain content.

    Returns an empty string when no usable text is available so callers can
    omit the snippet line entirely.
    """
    if not raw_content or not str(raw_content).strip():
        return ""

    text = re.sub(r"<[^>]+>", " ", str(raw_content))
    # Repair before whitespace collapse — \x85 is both UTF-8 mid-byte and \s.
    text = maybe_repair_mojibake(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return f"「{text}」"
    return f"「{text[:max_len].rstrip()}...」"


def references_heading_for_language(language: str) -> str:
    """Return the markdown heading for the references section."""
    normalized = (language or "chinese").lower()
    if normalized in ("chinese", "zh", "zh-cn", "zh-tw"):
        return "## 参考文献"
    return "## References"


class SourceRegistry:
    """Stable numbered source registry for in-text citations and reference lists."""

    def __init__(self, entries: list[dict[str, str]]):
        self.entries = entries

    @classmethod
    def from_research_sources(
        cls,
        sources: list[dict[str, Any]],
        fallback_urls: list[str] | None = None,
    ) -> SourceRegistry:
        """Build registry from scraped research sources with optional URL fallback."""
        entries: list[dict[str, str]] = []
        seen: set[str] = set()

        for source in sources or []:
            url = str(source.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            entries.append(
                {
                    "url": url,
                    "title": str(source.get("title") or "").strip(),
                    "raw_content": str(source.get("raw_content") or "").strip(),
                }
            )

        for url in fallback_urls or []:
            normalized = str(url).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                entries.append({"url": normalized, "title": "", "raw_content": ""})

        return cls(entries)

    def build_numbered_context(self, content_max_len: int = 400) -> str:
        """Format numbered source blocks for LLM context."""
        if not self.entries:
            return ""

        blocks: list[str] = []
        for index, entry in enumerate(self.entries, start=1):
            title = entry.get("title") or "Untitled"
            content = entry.get("raw_content") or ""
            if len(content) > content_max_len:
                content = content[:content_max_len].rstrip() + "..."
            blocks.append(
                f"[{index}] Title: {title}\n"
                f"    URL: {entry['url']}\n"
                f"    Content: {content}"
            )
        return "\n\n".join(blocks)

    def format_reference_list(self, references_heading: str | None = None) -> str:
        """Generate deterministic numbered reference section markdown."""
        if not self.entries:
            return ""

        heading = references_heading or "## 参考文献"
        lines = [heading, ""]
        use_chinese_labels = "参考文献" in heading
        for index, entry in enumerate(self.entries, start=1):
            domain = extract_domain(entry["url"])
            title = entry.get("title") or domain
            snippet = extract_snippet(entry.get("raw_content", ""))
            lines.append(f'<a id="ref-{index}"></a>**[{index}]** {domain} — {title}')
            lines.append(f"URL: {entry['url']}")
            # Only show snippet when scrape actually yielded text — avoid
            # noisy "原文不可用" placeholders for blocked/failed pages.
            if snippet:
                if use_chinese_labels:
                    lines.append(f"原文片段：{snippet}")
                else:
                    lines.append(f"Excerpt: {snippet}")
            lines.append("")

        return "\n".join(lines).rstrip()
