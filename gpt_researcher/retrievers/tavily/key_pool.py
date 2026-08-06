"""Tavily API key pool with automatic failover on quota exhaustion."""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Callable, Iterator, TypeVar

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_loaded_keys: list[str] = []
_exhausted_keys: set[str] = set()
_current_index = 0

T = TypeVar("T")

PLAN_LIMIT_STATUS_CODES = {403, 432, 433}


def _parse_keys(raw: str) -> list[str]:
    return [key.strip() for key in raw.split(",") if key.strip()]


def _load_keys_from_env() -> list[str]:
    multi_keys = _parse_keys(os.environ.get("TAVILY_API_KEYS", ""))
    if multi_keys:
        return multi_keys

    single_key = os.environ.get("TAVILY_API_KEY", "").strip()
    return [single_key] if single_key else []


def reload_tavily_keys() -> None:
    """Reload keys from environment (mainly for tests)."""
    global _loaded_keys, _exhausted_keys, _current_index
    with _lock:
        _loaded_keys = _load_keys_from_env()
        _exhausted_keys = set()
        _current_index = 0


def get_tavily_keys(include_exhausted: bool = False) -> list[str]:
    """Return configured Tavily API keys, excluding exhausted ones by default."""
    global _loaded_keys
    with _lock:
        if not _loaded_keys:
            _loaded_keys = _load_keys_from_env()
        if include_exhausted:
            return list(_loaded_keys)
        return [key for key in _loaded_keys if key not in _exhausted_keys]


def get_current_tavily_key(headers: dict | None = None) -> str:
    """Return the active Tavily key, honoring per-request header override."""
    if headers:
        header_key = headers.get("tavily_api_key")
        if header_key:
            return header_key

    available_keys = get_tavily_keys()
    if not available_keys:
        logger.warning(
            "Tavily API key not found. Set TAVILY_API_KEYS or TAVILY_API_KEY."
        )
        return ""

    global _current_index
    with _lock:
        index = _current_index % len(available_keys)
        return available_keys[index]


def _mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "***"
    return f"...{api_key[-8:]}"


def mark_tavily_key_exhausted(api_key: str, reason: str = "") -> None:
    """Mark a key as exhausted and advance to the next available key."""
    if not api_key:
        return

    global _current_index
    with _lock:
        if api_key not in _exhausted_keys:
            _exhausted_keys.add(api_key)
            logger.warning(
                "Tavily API key marked exhausted%s: %s",
                f" ({reason})" if reason else "",
                _mask_key(api_key),
            )

        available_keys = [key for key in _loaded_keys if key not in _exhausted_keys]
        if available_keys and api_key in _loaded_keys:
            previous_index = _loaded_keys.index(api_key)
            next_index = (previous_index + 1) % len(_loaded_keys)
            while _loaded_keys[next_index] in _exhausted_keys and next_index != previous_index:
                next_index = (next_index + 1) % len(_loaded_keys)
            if _loaded_keys[next_index] not in _exhausted_keys:
                _current_index = available_keys.index(_loaded_keys[next_index])
                logger.info(
                    "Switched to next Tavily API key: %s",
                    _mask_key(_loaded_keys[next_index]),
                )


def iter_tavily_keys(headers: dict | None = None) -> Iterator[str]:
    """Yield keys to try, starting with the current active key."""
    header_key = headers.get("tavily_api_key") if headers else None
    if header_key:
        yield header_key
        return

    seen: set[str] = set()
    keys = get_tavily_keys()
    if not keys:
        yield ""
        return

    start_key = get_current_tavily_key()
    ordered_keys = [start_key] + [key for key in keys if key != start_key]
    for key in ordered_keys:
        if key and key not in seen:
            seen.add(key)
            yield key


def _response_indicates_quota_exhaustion(status_code: int, body: str) -> bool:
    if status_code in PLAN_LIMIT_STATUS_CODES:
        return True

    normalized = body.lower()
    quota_markers = (
        "plan limit",
        "usage limit",
        "exceeds your plan",
        "quota",
        "credit",
        "billing",
    )
    return any(marker in normalized for marker in quota_markers)


def should_rotate_tavily_key(
    status_code: int | None = None,
    error_message: str = "",
    exception: Exception | None = None,
) -> bool:
    """Determine whether a Tavily failure should trigger key rotation."""
    message = error_message or ""
    code = status_code

    if exception is not None:
        message = message or str(exception)
        exception_name = exception.__class__.__name__.lower()
        if "invalidapikey" in exception_name:
            return True
        if "forbidden" in exception_name:
            return True
        if "usagelimitexceeded" in exception_name and _response_indicates_quota_exhaustion(
            429, message
        ):
            return True

    if code == 401:
        return True

    if code is not None and _response_indicates_quota_exhaustion(code, message):
        return True

    return _response_indicates_quota_exhaustion(0, message)


def parse_http_error_response(response) -> tuple[int, str]:
    """Extract status code and message from a requests response."""
    status_code = getattr(response, "status_code", 0) or 0
    body = ""
    try:
        payload = response.json()
        body = json.dumps(payload)
    except Exception:
        body = getattr(response, "text", "") or ""
    return status_code, body


def with_tavily_key_rotation(
    operation: Callable[[str], T],
    headers: dict | None = None,
) -> T:
    """Run an operation with automatic Tavily key failover."""
    last_error: Exception | None = None

    for api_key in iter_tavily_keys(headers):
        if not api_key:
            break
        try:
            return operation(api_key)
        except Exception as exc:
            last_error = exc
            if should_rotate_tavily_key(error_message=str(exc), exception=exc):
                mark_tavily_key_exhausted(api_key, reason=str(exc))
                continue
            raise

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "No Tavily API keys configured. Set TAVILY_API_KEYS or TAVILY_API_KEY."
    )
