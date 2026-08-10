"""Optional login/register + visitor migration endpoints. :-)"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from server.auth import (
    Identity,
    apply_identity_cookie,
    attach_auth_cookie,
    hash_password,
    mint_auth_token,
    new_registered_id,
    resolve_identity,
    verify_password,
)
from server.identity_store import (
    ensure_user,
    get_user_by_email,
    migrate_visitor_ownership,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterBody(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None


class LoginBody(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


@router.get("/me")
async def auth_me(request: Request, response: Response):
    ident = resolve_identity(request)
    await ensure_user(ident.user_id, kind=ident.kind)
    apply_identity_cookie(response, ident)
    return {
        "user_id": ident.user_id,
        "tenant_id": ident.tenant_id,
        "kind": ident.kind,
        "is_new": ident.is_new,
    }


@router.post("/register")
async def auth_register(body: RegisterBody, request: Request, response: Response):
    email = _normalize_email(body.email)
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="invalid email")
    existing = await get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="email already registered")

    visitor = resolve_identity(request)
    user_id = new_registered_id()
    pwd = hash_password(body.password)
    await ensure_user(
        user_id,
        kind="registered",
        email=email,
        display_name=(body.display_name or "").strip() or email.split("@")[0],
        password_hash=pwd,
    )
    migrated = await migrate_visitor_ownership(
        from_user_id=visitor.user_id, to_user_id=user_id
    )
    token = mint_auth_token(user_id)
    attach_auth_cookie(response, token)
    return {
        "user_id": user_id,
        "tenant_id": user_id,
        "kind": "registered",
        "email": email,
        "migrated": migrated,
    }


@router.post("/login")
async def auth_login(body: LoginBody, request: Request, response: Response):
    email = _normalize_email(body.email)
    row = await get_user_by_email(email)
    if not row or not verify_password(body.password, row.get("password_hash")):
        raise HTTPException(status_code=401, detail="invalid credentials")

    visitor = resolve_identity(request)
    user_id = row["id"]
    migrated = {"sessions": 0, "jobs": 0, "documents": 0, "chunks": 0}
    if visitor.kind == "visitor" and visitor.user_id.startswith("vis_"):
        migrated = await migrate_visitor_ownership(
            from_user_id=visitor.user_id, to_user_id=user_id
        )

    token = mint_auth_token(user_id)
    attach_auth_cookie(response, token)
    return {
        "user_id": user_id,
        "tenant_id": user_id,
        "kind": "registered",
        "email": row.get("email"),
        "migrated": migrated,
    }


@router.post("/logout")
async def auth_logout(request: Request, response: Response):
    # Clear registered cookie and mint a fresh visitor. :-)
    attach_auth_cookie(response, "", clear=True)
    fresh = Identity(
        user_id=__import__("server.auth", fromlist=["new_visitor_id"]).new_visitor_id(),
        tenant_id="",
        kind="visitor",
        is_new=True,
    )
    fresh.tenant_id = fresh.user_id
    fresh.set_cookie_value = mint_auth_token(fresh.user_id)
    await ensure_user(fresh.user_id, kind="visitor")
    apply_identity_cookie(response, fresh)
    request.state.gptr_identity = fresh
    return {"user_id": fresh.user_id, "kind": "visitor"}
