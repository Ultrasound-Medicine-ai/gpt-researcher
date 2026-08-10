"""Hard research budgets to prevent runaway model/search spend."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any


class BudgetExceeded(Exception):
    """Permanent failure: a hard research budget was exhausted."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def default_budget_limits() -> dict[str, int]:
    return {
        "max_total_searches": _env_int("RESEARCH_MAX_TOTAL_SEARCHES", 6),
        "max_output_words": _env_int("RESEARCH_MAX_OUTPUT_WORDS", 1800),
        "max_subtopics": _env_int("RESEARCH_MAX_SUBTOPICS", 2),
        "max_llm_calls": _env_int("RESEARCH_MAX_LLM_CALLS", 24),
    }


def count_words(text: str) -> int:
    """Approximate word count for CJK + Latin mixed text."""
    if not text:
        return 0
    cjk = re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]", text)
    latin = re.findall(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*", text)
    # Treat each CJK char as one word-equivalent for budget purposes
    return len(cjk) + len(latin)


def clamp_output_words(requested: int | None, hard_max: int | None = None) -> int:
    limits = default_budget_limits()
    cap = hard_max if hard_max is not None else limits["max_output_words"]
    if requested is None or requested <= 0:
        return cap
    return min(int(requested), cap)


# Numbered / trusted pipelines append refs under these headings. :-)
_REFERENCES_HEADING_RE = re.compile(
    r"(?:\n|^)(##\s*(?:References|参考文献)\s*\n)",
    re.IGNORECASE,
)


def split_body_and_references(text: str) -> tuple[str, str]:
    """Split report into body and trailing references section (incl. heading). :-)"""
    if not text:
        return "", ""
    matches = list(_REFERENCES_HEADING_RE.finditer(text))
    if not matches:
        return text, ""
    heading_start = matches[-1].start(1)
    return text[:heading_start].rstrip(), text[heading_start:]


def _truncate_body_to_words(text: str, max_words: int) -> str:
    """Truncate a body-only string; never used on the references tail. :-)"""
    if max_words <= 0 or not text:
        return text or ""
    if count_words(text) <= max_words:
        return text
    chars = list(text)
    words = 0
    cut = 0
    i = 0
    while i < len(chars):
        ch = chars[i]
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            words += 1
            cut = i + 1
            if words >= max_words:
                break
            i += 1
            continue
        if ch.isalnum():
            j = i
            while j < len(chars) and (chars[j].isalnum() or chars[j] in "'-"):
                j += 1
            words += 1
            cut = j
            if words >= max_words:
                break
            i = j
            continue
        i += 1
    trimmed = text[:cut].rstrip()
    if len(trimmed) < len(text):
        trimmed += "\n\n[truncated]"
    return trimmed


def truncate_to_words(text: str, max_words: int) -> str:
    """Apply word budget to report body only; keep 参考文献 / References intact. :-)"""
    if max_words <= 0 or not text:
        return text or ""
    body, references = split_body_and_references(text)
    if count_words(body) <= max_words:
        # Body already within budget — do not chop the reference list. :-)
        return text
    truncated_body = _truncate_body_to_words(body, max_words)
    if not references:
        return truncated_body
    return f"{truncated_body.rstrip()}\n\n{references.lstrip()}"


@dataclass
class ResearchBudget:
    max_total_searches: int = 12
    max_output_words: int = 3000
    max_subtopics: int = 3
    max_llm_calls: int = 40
    searches_used: int = 0
    llm_calls_used: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env_and_payload(cls, payload: dict | None = None) -> "ResearchBudget":
        limits = default_budget_limits()
        payload = payload or {}
        # Per-job overrides cannot exceed env hard caps
        max_searches = min(
            int(payload.get("max_total_searches") or limits["max_total_searches"]),
            limits["max_total_searches"],
        )
        requested_words = payload.get("total_words")
        max_words = clamp_output_words(
            int(requested_words) if requested_words is not None else None,
            limits["max_output_words"],
        )
        max_subtopics = min(
            int(payload.get("max_subtopics") or limits["max_subtopics"]),
            limits["max_subtopics"],
        )
        max_llm = min(
            int(payload.get("max_llm_calls") or limits["max_llm_calls"]),
            limits["max_llm_calls"],
        )
        return cls(
            max_total_searches=max_searches,
            max_output_words=max_words,
            max_subtopics=max_subtopics,
            max_llm_calls=max_llm,
        )

    def register_search(self, n: int = 1, where: str = "search") -> None:
        self.searches_used += n
        if self.max_total_searches > 0 and self.searches_used > self.max_total_searches:
            raise BudgetExceeded(
                "budget_exceeded",
                f"search budget exceeded at {where}: "
                f"{self.searches_used}/{self.max_total_searches}",
            )

    def register_llm_call(self, where: str = "llm") -> None:
        self.llm_calls_used += 1
        if self.max_llm_calls > 0 and self.llm_calls_used > self.max_llm_calls:
            raise BudgetExceeded(
                "budget_exceeded",
                f"llm call budget exceeded at {where}: "
                f"{self.llm_calls_used}/{self.max_llm_calls}",
            )

    def enforce_output_words(self, text: str) -> str:
        # Budget applies to prose body only; references are reattached intact. :-)
        return truncate_to_words(text, self.max_output_words)

    def clamp_subtopics(self, subtopics: list) -> list:
        if self.max_subtopics <= 0:
            return []
        return list(subtopics)[: self.max_subtopics]

    def snapshot(self) -> dict[str, Any]:
        return {
            "searches_used": self.searches_used,
            "max_total_searches": self.max_total_searches,
            "llm_calls_used": self.llm_calls_used,
            "max_llm_calls": self.max_llm_calls,
            "max_output_words": self.max_output_words,
            "max_subtopics": self.max_subtopics,
        }
