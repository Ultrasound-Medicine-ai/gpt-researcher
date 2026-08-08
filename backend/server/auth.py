"""Lightweight user / tenant identity from request headers (MVP, no OAuth).

No login required: missing headers → anonymous (unchanged for local UI testing).
"""

from __future__ import annotations

from fastapi import Request

DEFAULT_USER_ID = "anonymous"


def _header_str(request: Request | None, name: str) -> str | None:
    if request is None:
        return None
    val = request.headers.get(name) or request.headers.get(name.lower())
    if val and isinstance(val, str) and val.strip():
        return val.strip()[:64]
    return None


def resolve_user_id(request: Request | None = None) -> str:
    """Resolve user id from X-User-Id, default anonymous."""
    return _header_str(request, "X-User-Id") or DEFAULT_USER_ID


def resolve_tenant_id(request: Request | None = None, user_id: str | None = None) -> str:
    """Resolve tenant id from X-Tenant-Id, else same as user_id."""
    return _header_str(request, "X-Tenant-Id") or user_id or resolve_user_id(request)
