"""Unit tests for report intent / acronym disambiguation. :-)"""

from __future__ import annotations

import os

import pytest

from jobs import planning_context as pc


@pytest.fixture(autouse=True)
def _enable_planning(monkeypatch):
    monkeypatch.setenv("RESEARCH_USER_PLANNING_CONTEXT", "true")
    monkeypatch.setenv("RESEARCH_INTENT_CLARIFY", "true")
    monkeypatch.setenv("RESEARCH_AMBIGUITY_PREFERENCE", "tech")


def test_find_ambiguous_hits_sse():
    hits = pc.find_ambiguous_hits("帮我调研SSE，要求400字左右")
    assert len(hits) == 1
    assert hits[0]["token"] == "SSE"


def test_find_ambiguous_hits_already_clear():
    assert pc.find_ambiguous_hits("调研 Server-Sent Events (SSE)") == []
    assert pc.find_ambiguous_hits("上海证券交易所 SSE") == []


@pytest.mark.asyncio
async def test_resolve_clarifies_when_weak_history():
    result = await pc.resolve_report_intent(
        task="帮我调研SSE",
        user_id="u1",
        report_store=None,
        client_messages=[],
    )
    assert result["action"] == "clarify"
    assert result["confidence"] == "low"
    labels = {o["label"] for o in result["options"]}
    assert any("Server-Sent" in x for x in labels)
    assert any("Shanghai" in x or "上海" in x for x in labels)


@pytest.mark.asyncio
async def test_resolve_proceeds_with_tech_history():
    result = await pc.resolve_report_intent(
        task="调研SSE",
        user_id="u1",
        report_store=None,
        client_messages=[
            {"role": "user", "content": "我们前端用 websocket 和 eventsource 做推送"},
        ],
    )
    assert result["action"] == "proceed"
    assert "Server-Sent" in result["expanded_task"]


@pytest.mark.asyncio
async def test_resolve_force_sense():
    result = await pc.resolve_report_intent(
        task="调研SSE",
        user_id="u1",
        force_sense="Shanghai Stock Exchange (SSE; 上海证券交易所)",
    )
    assert result["action"] == "proceed"
    assert "上海证券" in result["expanded_task"] or "Shanghai" in result["expanded_task"]


@pytest.mark.asyncio
async def test_resolve_clarify_disabled_falls_back_tech(monkeypatch):
    monkeypatch.setenv("RESEARCH_INTENT_CLARIFY", "false")
    result = await pc.resolve_report_intent(task="调研SSE", user_id="u1")
    assert result["action"] == "proceed"
    assert "Server-Sent" in result["expanded_task"]
