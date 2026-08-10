"""Dependency resilience: circuit breakers, keyword fallback, degrade tracing.

Keeps report generation alive when search / scrape / embedding fail.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float = 0.0
    last_reason: str = ""


class CircuitBreaker:
    """Simple failure-count circuit with cooldown (half-open after TTL)."""

    def __init__(self, name: str, failure_threshold: int, cooldown_sec: float):
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_sec = max(1.0, cooldown_sec)
        self._state = CircuitState()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._state.failures < self.failure_threshold:
                return True
            if time.time() - self._state.opened_at >= self.cooldown_sec:
                # Half-open: allow one probe
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._state = CircuitState()

    def record_failure(self, reason: str = "") -> None:
        with self._lock:
            self._state.failures += 1
            self._state.last_reason = (reason or "")[:300]
            if self._state.failures >= self.failure_threshold:
                if self._state.opened_at <= 0:
                    self._state.opened_at = time.time()
                    logger.warning(
                        "Circuit '%s' OPEN after %s failures: %s",
                        self.name,
                        self._state.failures,
                        self._state.last_reason,
                    )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            open_ = (
                self._state.failures >= self.failure_threshold
                and time.time() - self._state.opened_at < self.cooldown_sec
            )
            return {
                "name": self.name,
                "open": open_,
                "failures": self._state.failures,
                "last_reason": self._state.last_reason,
            }


_circuits: dict[str, CircuitBreaker] = {}
_circuits_lock = threading.Lock()


def get_circuit(name: str) -> CircuitBreaker:
    with _circuits_lock:
        cb = _circuits.get(name)
        if cb is None:
            if name == "search":
                cb = CircuitBreaker(
                    name,
                    _env_int("RESEARCH_SEARCH_CIRCUIT_FAILURES", 4),
                    _env_float("RESEARCH_SEARCH_CIRCUIT_COOLDOWN_SEC", 90),
                )
            elif name == "scrape":
                cb = CircuitBreaker(
                    name,
                    _env_int("RESEARCH_SCRAPE_CIRCUIT_FAILURES", 8),
                    _env_float("RESEARCH_SCRAPE_CIRCUIT_COOLDOWN_SEC", 60),
                )
            else:
                cb = CircuitBreaker(
                    name,
                    _env_int("RESEARCH_EMBED_CIRCUIT_FAILURES", 3),
                    _env_float("RESEARCH_EMBED_CIRCUIT_COOLDOWN_SEC", 120),
                )
            _circuits[name] = cb
        return cb


def reset_circuits_for_tests() -> None:
    with _circuits_lock:
        _circuits.clear()


def scrape_url_timeout() -> float:
    # Fail fast on slow pages — long waits rarely yield usable text. :-)
    return _env_float("RESEARCH_SCRAPE_URL_TIMEOUT_SEC", 8)


def scrape_url_retries() -> int:
    # Default 0: avoid useless re-hits on timeouts / soft pages. :-)
    return _env_int("RESEARCH_SCRAPE_URL_RETRIES", 0)


def browse_chunk_max_length() -> int:
    # Keep scrape payloads lean for faster compression / LLM context. :-)
    return _env_int("BROWSE_CHUNK_MAX_LENGTH", 3072) or 3072


def tavily_search_timeout() -> float:
    return _env_float("RESEARCH_TAVILY_SEARCH_TIMEOUT_SEC", 12)


def tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", (query or "").lower())
    return [t for t in tokens if len(t) > 1][:24]


def keyword_score(text: str, tokens: list[str]) -> int:
    if not text:
        return 0
    low = text.lower()
    if not tokens:
        return 1
    return sum(low.count(t) for t in tokens)


def keyword_select_documents(
    query: str,
    documents: list[dict[str, Any]],
    *,
    max_results: int = 5,
    max_chars: int = 6000,
) -> list[dict[str, Any]]:
    """Rank raw scrape docs by simple keyword overlap (no embeddings)."""
    tokens = tokenize_query(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in documents or []:
        raw = str(doc.get("raw_content") or doc.get("page_content") or "")
        score = keyword_score(raw, tokens)
        if score > 0 or not tokens:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected: list[dict[str, Any]] = []
    total = 0
    for _, doc in scored[: max(max_results * 3, max_results)]:
        raw = str(doc.get("raw_content") or "")
        if total >= max_chars:
            break
        clipped = dict(doc)
        remain = max_chars - total
        if len(raw) > remain:
            clipped["raw_content"] = raw[:remain]
        selected.append(clipped)
        total += len(str(clipped.get("raw_content") or ""))
        if len(selected) >= max_results:
            break
    return selected


def keyword_snippet_from_text(query: str, text: str, *, max_chars: int = 6000) -> str:
    """Pull keyword-relevant windows from a free-form context blob (Chat path)."""
    if not text:
        return ""
    tokens = tokenize_query(query)
    if not tokens:
        return text[:max_chars]
    windows: list[tuple[int, str]] = []
    low = text.lower()
    for tok in tokens:
        start = 0
        while True:
            idx = low.find(tok, start)
            if idx < 0:
                break
            left = max(0, idx - 180)
            right = min(len(text), idx + 320)
            windows.append((idx, text[left:right]))
            start = idx + len(tok)
            if len(windows) >= 12:
                break
        if len(windows) >= 12:
            break
    if not windows:
        return text[:max_chars]
    windows.sort(key=lambda x: x[0])
    out: list[str] = []
    total = 0
    seen: set[str] = set()
    for _, chunk in windows:
        key = chunk[:80]
        if key in seen:
            continue
        seen.add(key)
        if total + len(chunk) > max_chars:
            break
        out.append(chunk.strip())
        total += len(chunk)
    return "\n...\n".join(out)


def record_degradation(subsystem: str, reason: str, **fields: Any) -> None:
    """Push degrade event into JobRuntime when available."""
    try:
        from jobs.runtime import get_abort_runtime

        runtime = get_abort_runtime()
        if runtime is None:
            return
        runtime.record_degradation(subsystem, reason, **fields)
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("record_degradation skipped: %s", exc)


async def persist_degradation_checkpoint() -> None:
    try:
        from jobs.runtime import get_abort_runtime

        runtime = get_abort_runtime()
        if runtime is not None:
            await runtime.save_checkpoint(degradations=runtime.degradations_snapshot())
    except Exception:
        pass


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"...{value[-8:]}"
