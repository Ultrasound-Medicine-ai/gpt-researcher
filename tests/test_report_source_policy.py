from types import SimpleNamespace

from rag import report_source_policy as policy


def _chunk(
    text: str = "x" * 1200,
    *,
    source_url: str = "https://example.test/source",
    source_type: str = "scrape",
    title: str = "Example source",
    chunk_id: str = "chunk-1",
):
    return SimpleNamespace(
        content=text,
        source_url=source_url,
        source_type=source_type,
        title=title,
        chunk_id=chunk_id,
        page_number=1,
    )


def test_local_first_uses_private_evidence_when_coverage_is_sufficient(monkeypatch):
    monkeypatch.setattr(policy, "hybrid_retrieve", lambda *args, **kwargs: [_chunk(), _chunk(), _chunk()])

    decision = policy.choose_report_sources(
        "解释 Redlock 算法", tenant_id="tenant-a", user_id="user-a", policy="local_first"
    )

    assert decision["mode"] == "knowledge_base"
    assert decision["reason"] == "sufficient_private_evidence"
    assert len(decision["chunks"]) == 3
    assert all(not policy._is_prior_report_chunk(c) for c in decision["chunks"])


def test_local_first_forces_web_for_freshness_and_never_uses_other_tenant(monkeypatch):
    seen = {}

    def retrieve(*args, **kwargs):
        seen.update(kwargs)
        return [_chunk(), _chunk(), _chunk()]

    monkeypatch.setattr(policy, "hybrid_retrieve", retrieve)
    decision = policy.choose_report_sources(
        "Redlock 算法最新进展", tenant_id="tenant-a", user_id="user-a", policy="local_first"
    )

    assert decision["mode"] == "web"
    assert decision["reason"] == "freshness_requested"
    assert seen["tenant_id"] == "tenant-a"
    assert seen["user_id"] == "user-a"
    assert seen["session_id"] is None


def test_prior_report_chunks_do_not_count_as_citable_evidence(monkeypatch):
    prior = _chunk(
        source_url="report:a390e1b3-f6fc-49dd-8508-55803132e5b6",
        source_type="report",
        title="FastAPI 技术评估报告",
        chunk_id="report-1",
    )
    monkeypatch.setattr(
        policy,
        "hybrid_retrieve",
        lambda *args, **kwargs: [prior, prior, prior],
    )

    decision = policy.choose_report_sources(
        "写个报告介绍 RESTful API",
        tenant_id="tenant-a",
        user_id="user-a",
        policy="local_first",
    )

    assert decision["mode"] == "web"
    assert decision["reason"] == "insufficient_private_evidence"
    assert decision["excluded_prior_reports"] == 3
    assert decision["chunks"] == []
    assert policy._is_prior_report_chunk(prior) is True
