"""Visitor + registered identity via signed HttpOnly cookie.

API does NOT trust client-supplied X-User-Id / X-Tenant-Id unless
ALLOW_TEST_USER_HEADERS=true (unit/e2e fixtures only). :-)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Request, Response

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "anonymous"  # legacy fallback; new traffic uses vis_* ids
COOKIE_NAME = os.getenv("VISITOR_COOKIE_NAME", "gptr_uid")
COOKIE_MAX_AGE_SEC = int(os.getenv("VISITOR_COOKIE_MAX_AGE_SEC", str(365 * 24 * 3600)))
COOKIE_PATH = "/"


def allow_test_user_headers() -> bool:
    return (os.getenv("ALLOW_TEST_USER_HEADERS") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _cookie_secret() -> bytes:
    raw = (os.getenv("VISITOR_COOKIE_SECRET") or os.getenv("SECRET_KEY") or "").strip()
    if not raw:
        # Dev fallback — set VISITOR_COOKIE_SECRET in production. :-)
        raw = "dev-only-visitor-cookie-secret-change-me"
        if (os.getenv("ENV") or "").lower() in ("production", "prod"):
            logger.error("VISITOR_COOKIE_SECRET is unset in production")
    return raw.encode("utf-8")


def new_visitor_id() -> str:
    return f"vis_{uuid.uuid4().hex}"


def new_registered_id() -> str:
    return f"usr_{uuid.uuid4().hex}"


def _sign(payload: str) -> str:
    return hmac.new(_cookie_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def mint_auth_token(user_id: str, *, max_age_sec: int | None = None) -> str:
    """Create signed cookie value: v1.<user_id>.<exp>.<sig>."""
    exp = int(time.time()) + int(max_age_sec or COOKIE_MAX_AGE_SEC)
    body = f"v1.{user_id}.{exp}"
    return f"{body}.{_sign(body)}"


def parse_auth_token(token: str | None) -> Optional[str]:
    if not token or not isinstance(token, str):
        return None
    parts = token.strip().split(".")
    if len(parts) != 4 or parts[0] != "v1":
        return None
    _, user_id, exp_s, sig = parts
    if not user_id or len(user_id) > 64:
        return None
    try:
        exp = int(exp_s)
    except ValueError:
        return None
    if exp < int(time.time()):
        return None
    body = f"v1.{user_id}.{exp_s}"
    expected = _sign(body)
    if not hmac.compare_digest(expected, sig):
        return None
    return user_id


def hash_password(password: str, *, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("pbkdf2_sha256$"):
        return False
    try:
        _, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    check = hash_password(password, salt=salt)
    return hmac.compare_digest(check, stored)


@dataclass
class Identity:
    user_id: str
    tenant_id: str
    kind: str = "visitor"  # visitor | registered
    is_new: bool = False
    set_cookie_value: Optional[str] = None


def _header_str(request: Request | None, name: str) -> str | None:
    if request is None:
        return None
    val = request.headers.get(name) or request.headers.get(name.lower())
    if val and isinstance(val, str) and val.strip():
        return val.strip()[:64]
    return None


def resolve_identity(request: Request | None = None) -> Identity:
    """Resolve identity from signed cookie (or test headers). Never trust prod X-User-Id."""
    if request is not None:
        cached = getattr(request.state, "gptr_identity", None)
        if isinstance(cached, Identity):
            return cached

    if allow_test_user_headers() and request is not None:
        hid = _header_str(request, "X-User-Id")
        if hid:
            tid = _header_str(request, "X-Tenant-Id") or hid
            ident = Identity(user_id=hid, tenant_id=tid, kind="registered", is_new=False)
            if request is not None:
                request.state.gptr_identity = ident
            return ident

    cookie_val = None
    if request is not None:
        cookie_val = request.cookies.get(COOKIE_NAME)
    user_id = parse_auth_token(cookie_val)
    if user_id:
        kind = "registered" if user_id.startswith("usr_") else "visitor"
        ident = Identity(user_id=user_id, tenant_id=user_id, kind=kind, is_new=False)
        if request is not None:
            request.state.gptr_identity = ident
        return ident

    # Mint a new visitor
    user_id = new_visitor_id()
    token = mint_auth_token(user_id)
    ident = Identity(
        user_id=user_id,
        tenant_id=user_id,
        kind="visitor",
        is_new=True,
        set_cookie_value=token,
    )
    if request is not None:
        request.state.gptr_identity = ident
    return ident


def resolve_user_id(request: Request | None = None) -> str:
    return resolve_identity(request).user_id


def resolve_tenant_id(request: Request | None = None, user_id: str | None = None) -> str:
    if request is not None:
        return resolve_identity(request).tenant_id
    return user_id or DEFAULT_USER_ID


def owner_filter(user_id: str) -> str:
    """Always scope data access to the resolved owner (no shared anonymous pool). :-)"""
    return user_id


def _cookie_secure() -> bool:
    """Secure cookies only when explicitly enabled.

    Do not infer from ENV=production — local docker defaults ENV to production
    while serving over HTTP via Next BFF, which would drop the cookie. :-)
    """
    return (os.getenv("VISITOR_COOKIE_SECURE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def attach_auth_cookie(response: Response, token: str, *, clear: bool = False) -> None:
    if clear:
        response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
        return
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE_SEC,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path=COOKIE_PATH,
    )


def apply_identity_cookie(response: Response, identity: Identity) -> Response:
    if identity.set_cookie_value:
        attach_auth_cookie(response, identity.set_cookie_value)
    return response
