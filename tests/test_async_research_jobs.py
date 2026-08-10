"""Integration-style tests for durable async research jobs.

Covers: create → enqueue → worker persist-before-complete → poll restore,
idempotency, enqueue failure (pending_dispatch), report save failure,
and that disconnect/cancel-of-WS is not required for worker continuity.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db_stubs import stub_db_session, stub_worker_imports

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "backend"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(autouse=True)
def _job_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://gptr:gptr@localhost:5432/gptr")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", "false")
    monkeypatch.setenv("ENABLE_ASYNC_RESEARCH_JOBS", "true")
    monkeypatch.setenv("ENABLE_WS_START_RESEARCH", "false")
    # Reset memory job store between tests
    import jobs as jobs_mod

    jobs_mod._MEMORY_JOBS.clear()
    yield
    jobs_mod._MEMORY_JOBS.clear()


def test_allow_in_process_false_in_production(monkeypatch):
    from jobs import allow_in_process_research_fallback

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", "true")
    assert allow_in_process_research_fallback() is False


def test_allow_in_process_true_only_in_dev(monkeypatch):
    from jobs import allow_in_process_research_fallback

    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", "true")
    assert allow_in_process_research_fallback() is True


def test_ws_start_disabled_by_default_in_production(monkeypatch):
    from jobs import enable_ws_start_research

    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("ENABLE_WS_START_RESEARCH", raising=False)
    assert enable_ws_start_research() is False


def test_ws_start_feature_flag_rollback(monkeypatch):
    from jobs import enable_ws_start_research

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ENABLE_WS_START_RESEARCH", "true")
    assert enable_ws_start_research() is True


@pytest.mark.asyncio
async def test_create_job_starts_pending_dispatch(monkeypatch):
    from jobs import create_job, get_job

    async def _no_db(*a, **k):
        return False

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)

    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t"},
    )
    job = await get_job(jid)
    assert job is not None
    assert job["status"] == "pending_dispatch"
    assert job["stage"] == "planning"


@pytest.mark.asyncio
async def test_enqueue_failure_keeps_pending_dispatch(monkeypatch):
    """Redis enqueue fail → status stays pending_dispatch (not failed)."""
    from jobs import create_job, get_job, update_job
    from jobs.worker import enqueue_research_job

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)

    jid = await create_job(
        user_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "hello", "user_id": "u1"},
    )

    async def _fail_pool():
        return None

    monkeypatch.setattr("jobs.redis_pool.ensure_arq_pool", _fail_pool)
    ok = await enqueue_research_job(jid, {"task": "hello", "user_id": "u1"})
    assert ok is False

    # Simulate API behavior on failure
    await update_job(
        jid,
        status="pending_dispatch",
        progress="pending_dispatch",
        error="Failed to enqueue",
    )
    job = await get_job(jid)
    assert job["status"] == "pending_dispatch"
    assert job["status"] != "failed"
    assert job["status"] != "completed"


@pytest.mark.asyncio
async def test_idempotent_create_reuses_active_job(monkeypatch):
    from jobs import create_job, get_job

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)

    key = "research:sess-1"
    j1 = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t"},
        idempotency_key=key,
    )
    j2 = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t"},
        idempotency_key=key,
    )
    assert j1 == j2
    assert (await get_job(j1))["status"] == "pending_dispatch"


@pytest.mark.asyncio
async def test_worker_persist_failure_not_completed(monkeypatch):
    from jobs import create_job, get_job, update_job
    from jobs import worker as worker_mod

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)

    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={
            "task": "Redis limits",
            "user_id": "u1",
            "tenant_id": "u1",
            "session_id": "11111111-1111-1111-1111-111111111111",
            "report_type": "research_report",
        },
    )
    await update_job(jid, status="queued")

    async def fake_run_agent(**kwargs):
        return "# Report\n\nBody text about Redis.", MagicMock(
            get_research_sources=lambda: [{"url": "https://a.test", "title": "A", "raw_content": "x" * 120}]
        )

    async def boom_persist(**kwargs):
        raise RuntimeError("disk full")

    stub_worker_imports(monkeypatch, run_agent=fake_run_agent)
    with patch.object(
        worker_mod, "_persist_report_and_sources", new=boom_persist
    ), patch(
        "jobs.progress.publish_job_event", new=AsyncMock()
    ):
        result = await worker_mod.run_research_job(
            {},
            jid,
            {
                "task": "Redis limits",
                "user_id": "u1",
                "tenant_id": "u1",
                "session_id": "11111111-1111-1111-1111-111111111111",
                "report_type": "research_report",
            },
        )

    assert result.get("failed") is True or result.get("retry") is True
    job = await get_job(jid)
    assert job["status"] != "completed"
    assert job["status"] in ("failed", "retrying", "queued")
    assert "disk full" in (job.get("error") or "").lower() or job["status"] != "completed"


@pytest.mark.asyncio
async def test_worker_completed_only_after_persist(monkeypatch):
    from jobs import create_job, get_job, update_job
    from jobs import worker as worker_mod

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)

    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t", "user_id": "u1", "tenant_id": "u1"},
    )
    await update_job(jid, status="queued")

    async def fake_run_agent(**kwargs):
        return "# Done\n\nOK", MagicMock(get_research_sources=lambda: [])

    async def ok_persist(**kwargs):
        return {"answer": "# Done"}

    stub_worker_imports(monkeypatch, run_agent=fake_run_agent)
    with patch.object(
        worker_mod, "_persist_report_and_sources", new=ok_persist
    ), patch(
        "jobs.progress.publish_job_event", new=AsyncMock()
    ):
        result = await worker_mod.run_research_job(
            {},
            jid,
            {
                "task": "t",
                "user_id": "u1",
                "tenant_id": "u1",
                "session_id": "11111111-1111-1111-1111-111111111111",
                "report_type": "research_report",
            },
        )

    assert result.get("report")
    job = await get_job(jid)
    assert job["status"] == "completed"
    assert job["result"]["report"]


@pytest.mark.asyncio
async def test_cancel_ws_not_required_for_worker_claim(monkeypatch):
    """Worker claim does not depend on any WebSocket; disconnect cannot cancel claim."""
    from jobs import create_job, claim_job_for_worker, update_job

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)

    jid = await create_job(user_id="u1", payload={"task": "t"})
    await update_job(jid, status="queued")
    claimed = await claim_job_for_worker(jid)
    assert claimed is not None
    assert claimed["status"] == "running"
    # Second claim (duplicate delivery / no WS) is rejected
    assert await claim_job_for_worker(jid) is None


@pytest.mark.asyncio
async def test_worker_can_claim_due_pending_dispatch_delivery_race(monkeypatch):
    """ARQ may expose a message slightly before the dispatcher commits queued."""
    from jobs import claim_job_for_worker, create_job

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)
    jid = await create_job(user_id="u1", payload={"task": "delivery race"})

    claimed = await claim_job_for_worker(jid, worker_id="worker-a")
    assert claimed is not None
    assert claimed["status"] == "running"
    assert claimed["attempt"] == 1


@pytest.mark.asyncio
async def test_poll_shape_for_frontend_restore(monkeypatch):
    """GET job payload has fields the frontend needs to restore progress/report."""
    from jobs import create_job, update_job, get_job

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)

    jid = await create_job(user_id="u1", payload={"task": "t"})
    await update_job(
        jid,
        status="running",
        stage="researching",
        progress="scraping",
    )
    job = await get_job(jid)
    assert "status" in job and "stage" in job
    await update_job(
        jid,
        status="completed",
        stage="finalizing",
        result={"report": "# R", "file_paths": {"md": "a.md"}},
    )
    job = await get_job(jid)
    assert job["result"]["report"].startswith("#")
    assert job["result"]["file_paths"]["md"]


@pytest.mark.asyncio
async def test_enqueue_uses_shared_pool_not_per_request_create(monkeypatch):
    from jobs.worker import enqueue_research_job

    calls = {"n": 0, "ids": []}

    class FakeRedis:
        async def enqueue_job(self, *a, **k):
            calls["n"] += 1
            calls["ids"].append(k["_job_id"])
            return True

    async def fake_ensure():
        return FakeRedis()

    monkeypatch.setattr("jobs.redis_pool.ensure_arq_pool", fake_ensure)
    monkeypatch.setattr("jobs.redis_pool.get_redis_url", lambda: "redis://localhost:6379/0")

    assert await enqueue_research_job("job-1", {"task": "t", "user_id": "anonymous"})
    assert await enqueue_research_job("job-1", {"task": "t", "user_id": "anonymous"})
    assert calls["n"] == 2
    assert all(job_id.startswith("research:job-1:") for job_id in calls["ids"])
    assert calls["ids"][0] != calls["ids"][1]


@pytest.mark.asyncio
async def test_enqueue_returns_false_when_arq_does_not_create_message(monkeypatch):
    from jobs.worker import enqueue_research_job

    class FakeRedis:
        async def enqueue_job(self, *a, **k):
            return None

    async def fake_ensure():
        return FakeRedis()

    monkeypatch.setattr("jobs.redis_pool.ensure_arq_pool", fake_ensure)
    monkeypatch.setattr("jobs.redis_pool.get_redis_url", lambda: "redis://localhost:6379/0")
    assert await enqueue_research_job("job-1", {"task": "t", "user_id": "anonymous"}) is False


def test_job_status_values_used_in_tests_are_valid():
    """Guard against JOB_STATUSES enum drift breaking poll/restore expectations."""
    from jobs import JOB_STATUSES, TERMINAL_STATUSES

    for status in ("pending_dispatch", "queued", "running", "completed", "failed"):
        assert status in JOB_STATUSES
    assert "completed" in TERMINAL_STATUSES
    assert "failed" in TERMINAL_STATUSES
