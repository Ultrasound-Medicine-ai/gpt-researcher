"""Reliability tests for durable ResearchJob lifecycle.

Covers idempotency, session bootstrap, dispatch recovery, stale reaper,
optimistic concurrency, error classification, cancellation, persistence
gating, migration checks, and production readiness.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import importlib.util

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "backend"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import jobs as jobs_mod


def _load_migration_check_module():
    path = ROOT / "backend" / "db" / "migration_check.py"
    spec = importlib.util.spec_from_file_location("_migration_check_under_test", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load migration_check from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _job_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://gptr:gptr@localhost:5432/gptr")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", "false")
    monkeypatch.setenv("ENABLE_ASYNC_RESEARCH_JOBS", "true")
    monkeypatch.setenv("ENABLE_WS_START_RESEARCH", "false")

    import jobs as jobs_mod
    from jobs.session_bootstrap import clear_session_bootstrap_cache

    jobs_mod._MEMORY_JOBS.clear()
    clear_session_bootstrap_cache()
    yield
    jobs_mod._MEMORY_JOBS.clear()
    clear_session_bootstrap_cache()


def _memory_only(monkeypatch):
    from db_stubs import stub_db_session

    monkeypatch.setattr("jobs._db_required", lambda: False)
    stub_db_session(monkeypatch, is_db_enabled=False)


# ---------------------------------------------------------------------------
# 1. Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_idempotency_key_returns_same_job_memory(monkeypatch):
    from jobs import create_job, get_job

    _memory_only(monkeypatch)
    key = "research:dup-1"
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
    assert len([j for j in jobs_mod._MEMORY_JOBS.values() if j.get("idempotency_key") == key]) == 1


@pytest.mark.asyncio
async def test_idempotency_db_lookup_reuses_active_job(monkeypatch):
    """DB idempotency lookup returns existing active job (post-insert race safety)."""
    from jobs import create_job
    from sqlalchemy.exc import IntegrityError

    key = "race-key"
    existing_id = "22222222-2222-2222-2222-222222222222"

    async def _fake_find(tenant_id, idempotency_key, *, user_id=None):
        if idempotency_key == key:
            return {"id": existing_id, "status": "pending_dispatch", "tenant_id": tenant_id}
        return None

    monkeypatch.setattr("jobs.find_job_by_idempotency", _fake_find)
    monkeypatch.setattr("jobs._db_required", lambda: False)

    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t"},
        idempotency_key=key,
    )
    assert jid == existing_id


@pytest.mark.asyncio
async def test_idempotency_post_race_lookup_reuses_job(monkeypatch):
    """Simulates post-IntegrityError retry: second lookup finds the existing row."""
    from jobs import create_job

    key = "db-dup"
    winner: dict[str, str | None] = {"id": None}

    async def _find(tenant_id, idempotency_key, *, user_id=None):
        if winner["id"]:
            return {
                "id": winner["id"],
                "status": "pending_dispatch",
                "tenant_id": tenant_id,
            }
        return None

    _memory_only(monkeypatch)
    monkeypatch.setattr("jobs.find_job_by_idempotency", _find)

    j1 = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t"},
        idempotency_key=key,
    )
    winner["id"] = j1
    j2 = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t"},
        idempotency_key=key,
    )
    assert j1 == j2


# ---------------------------------------------------------------------------
# 2–3. Session bootstrap (no session_id / no duplicate sessions)
# ---------------------------------------------------------------------------


class _MemoryReportStore:
    def __init__(self):
        self.sessions: dict[str, dict[str, Any]] = {}
        self.upsert_calls = 0

    async def upsert_report(
        self, report_id: str, report: dict[str, Any], user_id: str | None = None
    ) -> None:
        self.upsert_calls += 1
        self.sessions[report_id] = {**report, "id": report_id}


@pytest.mark.asyncio
async def test_no_session_id_auto_creates_session():
    from jobs.session_bootstrap import ensure_research_session

    store = _MemoryReportStore()
    sid = await ensure_research_session(
        report_store=store,
        user_id="u1",
        tenant_id="u1",
        task="What is Redis?",
    )
    assert sid
    assert sid in store.sessions
    assert store.sessions[sid]["question"] == "What is Redis?"
    assert store.sessions[sid]["status"] == "running"


@pytest.mark.asyncio
async def test_duplicate_request_does_not_create_multiple_sessions():
    from jobs.session_bootstrap import ensure_research_session

    store = _MemoryReportStore()
    key = "submit-once"
    s1 = await ensure_research_session(
        report_store=store,
        user_id="u1",
        tenant_id="u1",
        task="Same task",
        idempotency_key=key,
    )
    s2 = await ensure_research_session(
        report_store=store,
        user_id="u1",
        tenant_id="u1",
        task="Same task",
        idempotency_key=key,
    )
    assert s1 == s2
    assert store.upsert_calls == 1
    assert len(store.sessions) == 1


# ---------------------------------------------------------------------------
# 4–6. Dispatch: enqueue failure, recovery, no double-dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_enqueue_failure_keeps_pending_dispatch(monkeypatch):
    from jobs import create_job, get_job
    from jobs.worker import enqueue_research_job

    _memory_only(monkeypatch)

    jid = await create_job(
        user_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "hello", "user_id": "u1"},
    )

    async def _no_pool():
        return None

    monkeypatch.setattr("jobs.redis_pool.ensure_arq_pool", _no_pool)
    ok = await enqueue_research_job(jid, {"task": "hello", "user_id": "u1"})
    assert ok is False
    job = await get_job(jid)
    assert job["status"] == "pending_dispatch"


@pytest.mark.asyncio
async def test_dispatcher_recovers_and_enqueues(monkeypatch):
    from jobs import create_job, get_job
    from jobs.dispatcher import dispatch_pending_jobs

    _memory_only(monkeypatch)

    jid = await create_job(
        user_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "recover me", "user_id": "u1"},
    )

    calls = {"n": 0}

    async def _enqueue(job_id, payload, **kwargs):
        calls["n"] += 1
        return calls["n"] >= 2

    monkeypatch.setattr("jobs.worker.enqueue_research_job", _enqueue)

    first = await dispatch_pending_jobs()
    assert first == 0
    assert (await get_job(jid))["status"] == "pending_dispatch"

    jobs_mod._MEMORY_JOBS[jid]["next_retry_at"] = None

    second = await dispatch_pending_jobs()
    assert second == 1
    assert (await get_job(jid))["status"] == "queued"


@pytest.mark.asyncio
async def test_two_dispatcher_calls_do_not_double_dispatch(monkeypatch):
    """Memory path: once queued, pending_dispatch dispatcher skips the job (SKIP LOCKED semantics)."""
    from jobs import create_job
    from jobs.dispatcher import dispatch_pending_jobs

    _memory_only(monkeypatch)

    await create_job(
        user_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "once", "user_id": "u1"},
    )

    enqueue_calls: list[str] = []

    async def _enqueue(job_id, payload, **kwargs):
        enqueue_calls.append(job_id)
        assert kwargs == {"stamp_enqueued_at": False}
        return True

    monkeypatch.setattr("jobs.worker.enqueue_research_job", _enqueue)

    assert await dispatch_pending_jobs() == 1
    assert await dispatch_pending_jobs() == 0
    assert len(enqueue_calls) == 1


# ---------------------------------------------------------------------------
# 7. Worker duplicate job_id executes once
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_duplicate_job_id_claims_once(monkeypatch):
    from jobs import claim_job_for_worker, create_job, update_job

    _memory_only(monkeypatch)

    jid = await create_job(user_id="u1", payload={"task": "t"})
    await update_job(jid, status="queued")

    first = await claim_job_for_worker(jid, worker_id="worker-a")
    second = await claim_job_for_worker(jid, worker_id="worker-b")

    assert first is not None
    assert first["status"] == "running"
    assert second is None


# ---------------------------------------------------------------------------
# 8. Heartbeat timeout → stale → retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heartbeat_timeout_stale_then_triggers_dispatch(monkeypatch):
    from jobs import create_job, get_job, update_job
    from jobs.reaper import reap_stale_jobs

    _memory_only(monkeypatch)
    dispatch_calls = {"count": 0}

    async def _dispatch():
        dispatch_calls["count"] += 1
        return 1

    monkeypatch.setattr("jobs.dispatcher.dispatch_pending_jobs", _dispatch)

    jid = await create_job(user_id="u1", payload={"task": "stale test"})
    stale_ms = int((time.time() - 120) * 1000)
    await update_job(
        jid,
        status="running",
        worker_id="worker-old",
        heartbeat_at=stale_ms,
        attempt=1,
        version=2,
    )
    jobs_mod._MEMORY_JOBS[jid]["enqueued_at"] = int(time.time() * 1000)

    reaped = await reap_stale_jobs(stale_after_sec=60)
    assert reaped == 1
    job = await get_job(jid)
    assert job["status"] == "pending_dispatch"
    assert job.get("worker_id") is None
    assert dispatch_calls["count"] == 1


# ---------------------------------------------------------------------------
# 9. Old worker cannot overwrite new worker (optimistic version)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_old_worker_update_with_stale_version_fails(monkeypatch):
    from jobs import create_job, update_job, update_job_heartbeat

    _memory_only(monkeypatch)

    jid = await create_job(user_id="u1", payload={"task": "t"})
    await update_job(jid, status="running", worker_id="worker-new", version=5)
    jobs_mod._MEMORY_JOBS[jid]["version"] = 5

    ok = await update_job_heartbeat(jid, "worker-old", version=3)
    assert ok is False


# ---------------------------------------------------------------------------
# 10–11. Error classification: transient vs permanent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc,expected_code,transient",
    [
        (ConnectionError("connection reset by peer"), "connection_error", True),
        (TimeoutError("request timed out"), "timeout", True),
        (Exception("HTTP 429 too many requests"), "rate_limited", True),
        (Exception("redis connection refused"), "redis_unavailable", True),
        (PermissionError("403 forbidden"), "permission_denied", False),
        (ValueError("invalid parameter: task"), "bad_parameter", False),
        (Exception("content policy violation"), "content_policy", False),
        (Exception("cancel requested by user"), "cancelled", False),
    ],
)
def test_classify_error_transient_and_permanent(exc, expected_code, transient):
    from jobs.errors import classify_error

    code, is_transient = classify_error(exc)
    assert is_transient is transient
    assert code == expected_code


def test_backoff_seconds_increases_with_attempts():
    from jobs.errors import backoff_seconds

    delays = [backoff_seconds(i) for i in range(1, 5)]
    assert all(d >= 1 for d in delays)
    assert delays[0] <= delays[1] <= delays[2]


# ---------------------------------------------------------------------------
# 12. cancel_requested stops subsequent stages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_requested_raises_job_cancelled(monkeypatch):
    from jobs import cancel_job, create_job, update_job
    from jobs.runtime import JobCancelled, JobRuntime

    _memory_only(monkeypatch)

    jid = await create_job(user_id="u1", tenant_id="u1", payload={"task": "t"})
    await update_job(jid, status="running", worker_id="w1", version=2)
    await cancel_job(jid, tenant_id="u1")

    runtime = JobRuntime(jid, worker_id="w1", version=2, tenant_id="u1")
    with pytest.raises(JobCancelled):
        await runtime.check_cancel(where="researching")


@pytest.mark.asyncio
async def test_cancelling_progress_sink_stops_on_cancel(monkeypatch):
    from jobs import cancel_job, create_job, update_job
    from jobs.runtime import CancellingProgressSink, JobCancelled, JobRuntime

    _memory_only(monkeypatch)

    jid = await create_job(user_id="u1", tenant_id="u1", payload={"task": "t"})
    await update_job(jid, status="running", worker_id="w1", version=1)
    await cancel_job(jid, tenant_id="u1")

    inner = AsyncMock()
    runtime = JobRuntime(jid, worker_id="w1", version=1, tenant_id="u1")
    sink = CancellingProgressSink(inner, runtime)

    with pytest.raises(JobCancelled):
        await sink.send_json({"content": "scraping_urls"})

    inner.send_json.assert_not_called()


# ---------------------------------------------------------------------------
# 13. Cancelled job does not write completed Report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancelled_job_does_not_write_completed_report(monkeypatch):
    from jobs import create_job, get_job, update_job
    from jobs import worker as worker_mod
    from db_stubs import stub_worker_imports

    _memory_only(monkeypatch)

    sid = "33333333-3333-3333-3333-333333333333"
    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id=sid,
        payload={"task": "t", "user_id": "u1", "tenant_id": "u1", "session_id": sid},
    )
    await update_job(jid, status="cancelled")

    persist = AsyncMock()
    stub_worker_imports(monkeypatch)
    with patch.object(worker_mod, "_persist_report_and_sources", new=persist), patch(
        "jobs.progress.publish_job_event", new=AsyncMock()
    ):
        result = await worker_mod.run_research_job(
            {},
            jid,
            {"task": "t", "user_id": "u1", "tenant_id": "u1", "session_id": sid},
        )

    assert result.get("cancelled") or result.get("skipped")
    persist.assert_not_called()
    job = await get_job(jid)
    assert job["status"] == "cancelled"
    assert job["status"] != "completed"


# ---------------------------------------------------------------------------
# 14. Worker retry does not create duplicate Report (upsert same session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_retry_upserts_same_session_not_duplicate(monkeypatch):
    from jobs import create_job, get_job, update_job
    from jobs import worker as worker_mod
    from db_stubs import stub_worker_imports

    _memory_only(monkeypatch)

    sid = "44444444-4444-4444-4444-444444444444"
    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id=sid,
        payload={
            "task": "retry test",
            "user_id": "u1",
            "tenant_id": "u1",
            "session_id": sid,
            "report_type": "research_report",
        },
    )

    upsert_sessions: list[str] = []

    async def _track_persist(**kwargs):
        upsert_sessions.append(kwargs["session_id"])
        return {"answer": "# Report", "id": kwargs["session_id"]}

    async def fake_run_agent(**kwargs):
        return "# Report\n\nBody.", MagicMock(get_research_sources=lambda: [])

    params = {
        "task": "retry test",
        "user_id": "u1",
        "tenant_id": "u1",
        "session_id": sid,
        "report_type": "research_report",
    }

    stub_worker_imports(monkeypatch, run_agent=fake_run_agent)
    with patch.object(worker_mod, "_persist_report_and_sources", new=_track_persist), patch(
        "jobs.progress.publish_job_event", new=AsyncMock()
    ):
        await update_job(jid, status="queued")
        await worker_mod.run_research_job({}, jid, params)

        await update_job(jid, status="retrying")
        await worker_mod.run_research_job({}, jid, params)

    assert upsert_sessions == [sid, sid]
    assert len(set(upsert_sessions)) == 1
    assert (await get_job(jid))["status"] == "completed"


# ---------------------------------------------------------------------------
# 15. Report save failure does not mark completed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_save_failure_does_not_mark_completed(monkeypatch):
    from jobs import create_job, get_job, update_job
    from jobs import worker as worker_mod
    from db_stubs import stub_worker_imports

    _memory_only(monkeypatch)

    sid = "55555555-5555-5555-5555-555555555555"
    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id=sid,
        payload={
            "task": "persist fail",
            "user_id": "u1",
            "tenant_id": "u1",
            "session_id": sid,
            "report_type": "research_report",
        },
    )
    await update_job(jid, status="queued")

    async def fake_run_agent(**kwargs):
        return "# Report\n\nX", MagicMock(get_research_sources=lambda: [])

    async def boom_persist(**kwargs):
        raise RuntimeError("disk full")

    stub_worker_imports(monkeypatch, run_agent=fake_run_agent)
    with patch.object(worker_mod, "_persist_report_and_sources", new=boom_persist), patch(
        "jobs.progress.publish_job_event", new=AsyncMock()
    ):
        result = await worker_mod.run_research_job(
            {},
            jid,
            {
                "task": "persist fail",
                "user_id": "u1",
                "tenant_id": "u1",
                "session_id": sid,
                "report_type": "research_report",
            },
        )

    assert result.get("failed") is True
    job = await get_job(jid)
    assert job["status"] == "failed"
    assert job["status"] != "completed"


# ---------------------------------------------------------------------------
# 16. Migration version check helpers
# ---------------------------------------------------------------------------


def test_check_migrations_up_to_date_when_no_database_url(monkeypatch):
    migration_check = _load_migration_check_module()

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert migration_check.check_migrations_up_to_date() is True


def test_check_migrations_up_to_date_when_head_matches(monkeypatch):
    migration_check = _load_migration_check_module()

    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setattr(migration_check, "get_head_revision", lambda: "001")
    monkeypatch.setattr(migration_check, "get_current_revision", lambda: "001")
    assert migration_check.check_migrations_up_to_date() is True


def test_check_migrations_up_to_date_fails_on_drift(monkeypatch):
    migration_check = _load_migration_check_module()

    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setattr(migration_check, "get_head_revision", lambda: "002")
    monkeypatch.setattr(migration_check, "get_current_revision", lambda: "001")
    assert migration_check.check_migrations_up_to_date() is False


def test_check_migrations_fails_when_head_unavailable(monkeypatch):
    migration_check = _load_migration_check_module()

    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setattr(migration_check, "get_head_revision", lambda: None)
    monkeypatch.setattr(migration_check, "get_current_revision", lambda: "001")
    assert migration_check.check_migrations_up_to_date() is False


# ---------------------------------------------------------------------------
# 17. Readiness fails without DATABASE_URL/REDIS_URL in production
# ---------------------------------------------------------------------------


def test_readiness_fails_without_database_and_redis_in_production(monkeypatch):
    from server.health import check_readiness

    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    ok, issues = check_readiness()
    assert ok is False
    assert any("DATABASE_URL" in i for i in issues)
    assert any("REDIS_URL" in i for i in issues)


def test_readiness_ok_in_production_with_urls_and_migrations(monkeypatch):
    from server.health import check_readiness

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    migration_check = _load_migration_check_module()
    monkeypatch.setattr(
        migration_check, "check_migrations_up_to_date", lambda: True, raising=False
    )
    with patch.dict(sys.modules, {"db.migration_check": migration_check}):
        ok, issues = check_readiness()
    assert ok is True
    assert issues == []


def test_readiness_allows_missing_urls_outside_production(monkeypatch):
    from server.health import check_readiness

    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    ok, issues = check_readiness()
    assert ok is True
    assert issues == []


# ---------------------------------------------------------------------------
# Status enum compatibility (guards test_async_research_jobs expectations)
# ---------------------------------------------------------------------------


def test_job_status_enums_include_async_job_lifecycle():
    from jobs import JOB_STATUSES, JOB_STAGES, TERMINAL_STATUSES

    for status in (
        "pending_dispatch",
        "queued",
        "running",
        "retrying",
        "stale",
        "cancel_requested",
        "completed",
        "failed",
        "cancelled",
    ):
        assert status in JOB_STATUSES
    assert "completed" in TERMINAL_STATUSES
    assert "planning" in JOB_STAGES


# ---------------------------------------------------------------------------
# Hard budgets
# ---------------------------------------------------------------------------


def test_budget_clamps_output_words(monkeypatch):
    monkeypatch.setenv("RESEARCH_MAX_OUTPUT_WORDS", "500")
    from jobs.budget import ResearchBudget, clamp_output_words, count_words, truncate_to_words

    assert clamp_output_words(300) == 300
    assert clamp_output_words(9000) == 500
    budget = ResearchBudget.from_env_and_payload({"total_words": 1200})
    assert budget.max_output_words == 500
    text = "词 " * 2000
    out = budget.enforce_output_words(text)
    assert count_words(out) <= 520
    assert "truncated" in out.lower() or count_words(out) <= 500
    clipped = truncate_to_words("hello world again", 2)
    assert clipped.startswith("hello world")
    assert "[truncated]" in clipped


def test_truncate_preserves_chinese_references_section():
    from jobs.budget import count_words, truncate_to_words

    body = "汉字内容" * 400  # well over 100 CJK "words"
    references = (
        "## 参考文献\n\n"
        '<a id="ref-1"></a>**[1]** example.com — 标题一\n'
        "URL: https://example.com/one\n"
        "原文片段：「完整片段不应被截断」\n\n"
        '<a id="ref-2"></a>**[2]** example.org — 标题二\n'
        "URL: https://example.org/two\n"
        "原文片段：「第二条也必须保留」\n"
    )
    report = f"{body}\n\n{references}"
    out = truncate_to_words(report, 100)
    body_out, _, refs_out = out.partition("## 参考文献")
    assert count_words(body_out) <= 110
    assert "[truncated]" in body_out
    assert 'id="ref-1"' in refs_out
    assert 'id="ref-2"' in refs_out
    assert "完整片段不应被截断" in refs_out
    assert "第二条也必须保留" in refs_out
    assert "[truncated]" not in refs_out


def test_truncate_preserves_english_references_when_body_fits():
    from jobs.budget import truncate_to_words

    report = (
        "Short body with citation [1].\n\n"
        "## References\n\n"
        "[1] Source — https://example.com\n"
    )
    out = truncate_to_words(report, 50)
    assert out == report


def test_budget_search_exceeded_is_permanent():
    from jobs.budget import BudgetExceeded, ResearchBudget
    from jobs.errors import classify_error

    budget = ResearchBudget(max_total_searches=2, max_output_words=100, max_llm_calls=10)
    budget.register_search(1, where="a")
    budget.register_search(1, where="b")
    try:
        budget.register_search(1, where="c")
        assert False, "expected BudgetExceeded"
    except BudgetExceeded as exc:
        code, transient = classify_error(exc)
        assert code == "budget_exceeded"
        assert transient is False


def test_budget_clamps_subtopics():
    from jobs.budget import ResearchBudget

    budget = ResearchBudget(max_subtopics=2)
    topics = [{"task": "a"}, {"task": "b"}, {"task": "c"}]
    assert budget.clamp_subtopics(topics) == [{"task": "a"}, {"task": "b"}]


@pytest.mark.asyncio
async def test_abort_check_raises_on_cancel_requested(monkeypatch):
    from jobs import create_job, update_job
    from jobs.runtime import JobCancelled, JobRuntime, set_abort_runtime, reset_abort_runtime

    _memory_only = lambda mp: (
        mp.setattr("jobs._db_required", lambda: False),
        mp.setattr("db.session.is_db_enabled", lambda: False),
    )
    monkeypatch.setattr("jobs._db_required", lambda: False)
    try:
        from tests.db_stubs import stub_db_session

        stub_db_session(monkeypatch, is_db_enabled=False)
    except Exception:
        monkeypatch.setattr("db.session.is_db_enabled", lambda: False)

    jid = await create_job(
        user_id="u1",
        tenant_id="u1",
        session_id="11111111-1111-1111-1111-111111111111",
        payload={"task": "t"},
    )
    await update_job(jid, status="running", worker_id="w1")
    await update_job(jid, status="cancel_requested")
    runtime = JobRuntime(jid, "w1", 1, tenant_id="u1")
    token = set_abort_runtime(runtime)
    try:
        with pytest.raises(JobCancelled):
            await runtime.abort_check("unit_test")
    finally:
        reset_abort_runtime(token)
