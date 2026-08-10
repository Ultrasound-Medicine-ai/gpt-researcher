"""Research job error classification and retry backoff."""

from __future__ import annotations

import random
import re
from typing import Tuple

TRANSIENT_KEYWORDS = (
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "connection aborted",
    "connection closed",
    "broken pipe",
    "temporarily unavailable",
    "service unavailable",
    "too many requests",
    "rate limit",
    "429",
    "502",
    "503",
    "504",
    "5xx",
    "redis",
    "database",
    "db unavailable",
    "pool timeout",
    "deadlock",
    "could not connect",
    "network",
    "socket",
    "econnreset",
    "econnrefused",
    "enqueu",
    "queue full",
)

PERMANENT_KEYWORDS = (
    "unauthorized",
    "authentication",
    "auth failed",
    "forbidden",
    "permission denied",
    "invalid api key",
    "bad request",
    "invalid parameter",
    "bad param",
    "validation error",
    "unsafe url",
    "blocked url",
    "cancelled",
    "canceled",
    "cancel requested",
    "content policy",
    "content filter",
    "safety",
    "not allowed",
    "malformed",
    "unsupported",
)

_TRANSIENT_RE = re.compile("|".join(re.escape(k) for k in TRANSIENT_KEYWORDS), re.I)
_PERMANENT_RE = re.compile("|".join(re.escape(k) for k in PERMANENT_KEYWORDS), re.I)

_BACKOFF_BASES = (5, 30, 120)


def _normalize_message(exc: BaseException) -> str:
    parts = [str(exc)]
    for attr in ("message", "detail", "body"):
        val = getattr(exc, attr, None)
        if val:
            parts.append(str(val))
    cause = exc.__cause__
    if cause is not None:
        parts.append(str(cause))
    return " ".join(parts).lower()


def classify_error(exc: BaseException) -> Tuple[str, bool]:
    """
    Return (error_code, is_transient).

    error_code is a short snake_case identifier suitable for last_error_code.
    """
    # BudgetExceeded is always permanent
    code_attr = getattr(exc, "code", None)
    if code_attr == "budget_exceeded" or type(exc).__name__ == "BudgetExceeded":
        return "budget_exceeded", False
    if "budget_exceeded" in type(exc).__name__.lower():
        return "budget_exceeded", False
    if code_attr == "citation_audit_failed" or type(exc).__name__ == "CitationAuditFailed":
        return "citation_audit_failed", False

    msg = _normalize_message(exc)
    name = type(exc).__name__.lower()

    if "budget" in msg and "exceed" in msg:
        return "budget_exceeded", False

    if "citation_audit" in msg or "citationaudit" in name:
        return "citation_audit_failed", False

    if "cancel" in msg or "cancel" in name:
        return "cancelled", False

    status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status_code is not None:
        try:
            code = int(status_code)
            if code == 429 or code >= 500:
                return f"http_{code}", True
            if 400 <= code < 500:
                return f"http_{code}", False
        except (TypeError, ValueError):
            pass

    if _PERMANENT_RE.search(msg) or _PERMANENT_RE.search(name):
        if "unsafe" in msg or "blocked url" in msg:
            return "unsafe_url", False
        if "content policy" in msg or "content filter" in msg or "safety" in msg:
            return "content_policy", False
        if "permission" in msg or "forbidden" in msg:
            return "permission_denied", False
        if "auth" in msg or "unauthorized" in msg:
            return "auth_failed", False
        if "invalid" in msg or "bad param" in msg or "validation" in msg:
            return "bad_parameter", False
        return "permanent_error", False

    if _TRANSIENT_RE.search(msg) or _TRANSIENT_RE.search(name):
        if "429" in msg or "rate limit" in msg or "too many requests" in msg:
            return "rate_limited", True
        if "timeout" in msg or "timed out" in msg:
            return "timeout", True
        if "redis" in msg:
            return "redis_unavailable", True
        if "database" in msg or "db unavailable" in msg:
            return "db_unavailable", True
        if "connection" in msg or "socket" in msg or "network" in msg:
            return "connection_error", True
        return "transient_error", True

    return "unknown_error", False


def backoff_seconds(attempt: int) -> int:
    """Exponential-ish backoff with jitter: ~5s, ~30s, ~120s."""
    idx = max(0, min(attempt - 1, len(_BACKOFF_BASES) - 1))
    base = _BACKOFF_BASES[idx]
    jitter = random.uniform(0.85, 1.15)
    return max(1, int(base * jitter))
