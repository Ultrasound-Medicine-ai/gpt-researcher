"""Unit tests for research job concurrency slots and daily budget gates."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "backend"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("RESEARCH_MAX_CONCURRENT_PER_USER", "1")
    monkeypatch.setenv("RESEARCH_MAX_CONCURRENT_GLOBAL", "2")
    monkeypatch.setenv("RESEARCH_MAX_QUEUE_DEPTH", "2")
    monkeypatch.setenv("RESEARCH_LIMIT_RETRY_AFTER_SEC", "30")
    monkeypatch.setenv("RESEARCH_DAILY_MAX_SEARCHES", "50")
    monkeypatch.setenv("RESEARCH_DAILY_MAX_LLM_CALLS", "200")


@pytest.mark.asyncio
async def test_precheck_rejects_user_concurrency(monkeypatch):
    from jobs import slots

    async def fake_count(*, tenant_id=None, user_id=None):
        if user_id:
            return 1
        return 1

    monkeypatch.setattr(slots, "count_active_jobs_pg", fake_count)
    reject = await slots.precheck_capacity(tenant_id="t1", user_id="u1")
    assert reject is not None
    assert reject.code == "user_concurrency_limit"
    assert reject.retry_after == 30


@pytest.mark.asyncio
async def test_precheck_rejects_global_concurrency(monkeypatch):
    from jobs import slots

    async def fake_count(*, tenant_id=None, user_id=None):
        if user_id:
            return 0
        return 2

    monkeypatch.setattr(slots, "count_active_jobs_pg", fake_count)
    reject = await slots.precheck_capacity(tenant_id="t1", user_id="u2")
    assert reject is not None
    assert reject.code in ("global_concurrency_limit", "queue_full")


@pytest.mark.asyncio
async def test_acquire_slots_lua_success():
    from jobs import slots

    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=[1, "ok"])

    with patch.object(slots, "_redis", AsyncMock(return_value=redis)):
        await slots.acquire_slots(tenant_id="t", user_id="u", job_id="j1")
    redis.eval.assert_awaited()


@pytest.mark.asyncio
async def test_acquire_slots_lua_user_limit():
    from jobs import slots

    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=[0, "user_concurrency_limit"])

    with patch.object(slots, "_redis", AsyncMock(return_value=redis)):
        with pytest.raises(slots.SlotAcquireError) as exc:
            await slots.acquire_slots(tenant_id="t", user_id="u", job_id="j1")
    assert exc.value.reject.code == "user_concurrency_limit"


@pytest.mark.asyncio
async def test_release_slots_calls_lua():
    from jobs import slots

    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=1)

    with patch.object(slots, "_redis", AsyncMock(return_value=redis)):
        await slots.release_slots(job_id="j1", tenant_id="t", user_id="u")
    redis.eval.assert_awaited()


@pytest.mark.asyncio
async def test_reap_leaked_slots_releases_terminal():
    from jobs import slots

    redis = AsyncMock()
    redis.smembers = AsyncMock(return_value={"dead-job"})
    redis.ttl = AsyncMock(return_value=-2)
    redis.scard = AsyncMock(return_value=0)
    redis.eval = AsyncMock(return_value=1)

    with patch.object(slots, "_redis", AsyncMock(return_value=redis)):
        with patch("jobs.get_job", AsyncMock(return_value={"status": "completed", "tenant_id": "t", "user_id": "u"})):
            with patch.object(slots, "_rebuild_slots_from_pg", AsyncMock(return_value=0)):
                n = await slots.reap_leaked_slots()
    assert n == 1


@pytest.mark.asyncio
async def test_daily_budget_reject(monkeypatch):
    from jobs import daily_budget

    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=lambda k: b"50" if "searches" in k else b"0")

    with patch("jobs.redis_pool.get_redis", AsyncMock(return_value=redis)):
        with pytest.raises(daily_budget.DailyBudgetReject) as exc:
            await daily_budget.check_daily_budget(tenant_id="t", user_id="u")
    assert exc.value.code == "daily_search_budget_exceeded"


@pytest.mark.asyncio
async def test_http_429_detail_shape():
    from jobs.slots import SlotReject, http_429_detail

    detail = http_429_detail(
        SlotReject(code="queue_full", message="队列已满", retry_after=60)
    )
    assert detail["error_code"] == "queue_full"
    assert detail["retry_after"] == 60
