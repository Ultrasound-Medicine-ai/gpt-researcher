"""Job enqueue policy: production must not fall back to in-process execution."""

import pytest


def test_forbid_in_process_when_env_production(monkeypatch):
    from jobs import allow_in_process_research_fallback
    from jobs.worker import forbid_in_process_jobs

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", "true")
    assert allow_in_process_research_fallback() is False
    assert forbid_in_process_jobs() is True


def test_allow_in_process_only_with_explicit_true_outside_prod(monkeypatch):
    from jobs import allow_in_process_research_fallback
    from jobs.worker import forbid_in_process_jobs

    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", "true")
    assert allow_in_process_research_fallback() is True
    assert forbid_in_process_jobs() is False


def test_default_disallows_in_process_fallback(monkeypatch):
    from jobs import allow_in_process_research_fallback

    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", raising=False)
    assert allow_in_process_research_fallback() is False


@pytest.mark.asyncio
async def test_enqueue_without_redis_returns_false(monkeypatch):
    from jobs.worker import enqueue_research_job

    monkeypatch.setattr("jobs.redis_pool.get_redis_url", lambda: "")
    ok = await enqueue_research_job("job-x", {"task": "t", "user_id": "anonymous"})
    assert ok is False
