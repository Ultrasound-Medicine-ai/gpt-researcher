"""Visitor cookie identity + isolation gates (no LLM). :-)"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


class _Headers(dict):
    def get(self, key, default=None):
        if key in self:
            return self[key]
        return dict.get(self, str(key).lower(), default)


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setenv("VISITOR_COOKIE_SECRET", "unit-test-secret")
    monkeypatch.delenv("ALLOW_TEST_USER_HEADERS", raising=False)


def test_mint_and_parse_auth_token_roundtrip():
    from server.auth import mint_auth_token, parse_auth_token

    token = mint_auth_token("vis_abc123")
    assert parse_auth_token(token) == "vis_abc123"
    assert parse_auth_token("v1.vis_abc123.9999999999.deadbeef") is None
    assert parse_auth_token(None) is None


def test_cookie_secure_not_inferred_from_env_production(monkeypatch):
    from server.auth import _cookie_secure

    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("VISITOR_COOKIE_SECURE", raising=False)
    assert _cookie_secure() is False
    monkeypatch.setenv("VISITOR_COOKIE_SECURE", "true")
    assert _cookie_secure() is True


def test_resolve_identity_ignores_x_user_id_by_default():
    from server.auth import resolve_identity

    req = SimpleNamespace(cookies={}, headers=_Headers({"X-User-Id": "attacker"}), state=SimpleNamespace())
    ident = resolve_identity(req)
    assert ident.user_id.startswith("vis_")
    assert ident.user_id != "attacker"
    assert ident.is_new is True
    assert ident.set_cookie_value


def test_test_headers_only_when_allowlisted(monkeypatch):
    from server.auth import resolve_identity

    monkeypatch.setenv("ALLOW_TEST_USER_HEADERS", "true")
    req = SimpleNamespace(
        cookies={},
        headers=_Headers({"X-User-Id": "test-user", "X-Tenant-Id": "test-tenant"}),
        state=SimpleNamespace(),
    )
    ident = resolve_identity(req)
    assert ident.user_id == "test-user"
    assert ident.tenant_id == "test-tenant"


def test_cookie_restores_same_visitor():
    from server.auth import COOKIE_NAME, mint_auth_token, resolve_identity

    token = mint_auth_token("vis_stable")
    req = SimpleNamespace(
        cookies={COOKIE_NAME: token},
        headers=_Headers(),
        state=SimpleNamespace(),
    )
    ident = resolve_identity(req)
    assert ident.user_id == "vis_stable"
    assert ident.is_new is False
    assert ident.set_cookie_value is None


def test_password_hash_verify():
    from server.auth import hash_password, verify_password

    h = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_get_job_enforces_owner_match():
    from jobs import _MEMORY_JOBS, get_job

    _MEMORY_JOBS.clear()
    _MEMORY_JOBS["job-1"] = {
        "id": "job-1",
        "user_id": "vis_owner",
        "tenant_id": "vis_owner",
        "status": "running",
        "stage": "writing",
        "progress": "x",
    }

    async def _run():
        assert await get_job("job-1", tenant_id="vis_owner", user_id="vis_owner")
        assert await get_job("job-1", tenant_id="vis_other", user_id="vis_other") is None
        assert await get_job("job-1", tenant_id="vis_owner", user_id="anonymous") is None

    asyncio.run(_run())
    _MEMORY_JOBS.clear()


def test_chat_report_request_shape():
    from server.chat_report_request import chat_report_request

    out = chat_report_request("Redis 原理", "500字")
    assert out["action"] == "create_report"
    assert "Redis" in out["task"]
    assert out["knowledge_policy"] == "local_first"


def test_owner_filter_never_none():
    from server.auth import owner_filter

    assert owner_filter("vis_x") == "vis_x"
    assert owner_filter("anonymous") == "anonymous"


def test_migrate_visitor_skips_non_visitor():
    from server.identity_store import migrate_visitor_ownership

    async def _run():
        stats = await migrate_visitor_ownership(
            from_user_id="usr_already", to_user_id="usr_other"
        )
        assert stats["sessions"] == 0
        assert stats["jobs"] == 0
        same = await migrate_visitor_ownership(
            from_user_id="vis_x", to_user_id="vis_x"
        )
        assert same["sessions"] == 0

    asyncio.run(_run())


def test_migrate_visitor_noop_when_db_disabled(monkeypatch):
    """When DB is off, migrate returns zero counts (no LLM). :-)"""
    import types
    from unittest.mock import AsyncMock

    from server import identity_store

    fake = types.ModuleType("db.session")
    fake.is_db_enabled = lambda: False
    fake.get_session_factory = lambda: None
    monkeypatch.setitem(sys.modules, "db.session", fake)
    monkeypatch.setattr(identity_store, "ensure_user", AsyncMock())

    async def _run():
        stats = await identity_store.migrate_visitor_ownership(
            from_user_id="vis_from", to_user_id="usr_to"
        )
        assert stats["sessions"] == 0
        assert stats["jobs"] == 0
        assert stats["documents"] == 0
        assert stats["to_user_id"] == "usr_to"

    asyncio.run(_run())
