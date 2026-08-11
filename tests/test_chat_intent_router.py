from __future__ import annotations

import pytest

from chat.intent_router import (
    ChatIntent,
    IntentAction,
    IntentTarget,
    apply_intent_policy,
    classify_chat_intent,
    fallback_intent,
)
from evals._common import build_intent_metrics


@pytest.mark.asyncio
async def test_structured_router_parses_llm_json() -> None:
    async def completion(**_kwargs) -> str:
        return """{
          "action": "transform_report",
          "target": "current_report",
          "rewritten_query": "总结当前报告",
          "confidence": 0.96,
          "clarification_question": "",
          "reason": "current report is explicit"
        }"""

    intent = await classify_chat_intent(
        latest_message="帮我总结一下这个报告",
        has_report=True,
        report_topic="Redis",
        messages=[{"role": "user", "content": "帮我总结一下这个报告"}],
        model="router-model",
        llm_provider="test",
        completion=completion,
    )

    assert intent.action == IntentAction.TRANSFORM_REPORT
    assert intent.target == IntentTarget.CURRENT_REPORT
    assert intent.source == "llm"


@pytest.mark.asyncio
async def test_invalid_llm_output_falls_back_without_creating_report() -> None:
    async def completion(**_kwargs) -> str:
        return "not-json"

    intent = await classify_chat_intent(
        latest_message="帮我总结一下这个报告",
        has_report=True,
        report_topic="Redis",
        messages=[],
        model="router-model",
        llm_provider="test",
        completion=completion,
    )
    decision = apply_intent_policy(
        intent,
        has_report=True,
        report_creation_available=True,
    )

    assert intent.action == IntentAction.TRANSFORM_REPORT
    assert intent.source == "fallback"
    assert decision.action == "answer_in_chat"
    assert decision.allow_report_side_effect is False


def test_explicit_new_redis_report_can_request_creation() -> None:
    intent = fallback_intent("写一份Redis调研报告", has_report=True)
    decision = apply_intent_policy(
        intent,
        has_report=True,
        report_creation_available=True,
        permission_granted=True,
        budget_available=True,
    )

    assert intent.action == IntentAction.CREATE_RESEARCH_REPORT
    assert intent.target == IntentTarget.NEW_TOPIC
    assert decision.action == "request_report_creation"
    assert decision.allow_report_side_effect is True


@pytest.mark.asyncio
async def test_report_choice_resolves_previous_clarification_without_llm() -> None:
    called = False

    async def completion(**_kwargs) -> str:
        nonlocal called
        called = True
        raise AssertionError("dialogue-state choice should not call the router LLM")

    intent = await classify_chat_intent(
        latest_message="基于这个报告继续回答",
        has_report=True,
        report_topic="Redis",
        messages=[
            {"role": "user", "content": "继续分析它的持久化方案"},
            {
                "role": "assistant",
                "content": "你希望我基于当前报告继续回答，还是创建一份新的独立研究报告？",
            },
            {"role": "user", "content": "基于这个报告继续回答"},
        ],
        model="router-model",
        llm_provider="test",
        completion=completion,
    )
    decision = apply_intent_policy(
        intent,
        has_report=True,
        report_creation_available=True,
    )

    assert called is False
    assert intent.action == IntentAction.ANSWER_FROM_REPORT
    assert intent.target == IntentTarget.CURRENT_REPORT
    assert intent.rewritten_query == "继续分析它的持久化方案"
    assert intent.source == "dialogue_state"
    assert decision.action == "answer_in_chat"
    assert decision.allow_report_side_effect is False


def test_current_report_choice_is_safe_fallback_without_history() -> None:
    intent = fallback_intent("基于这个报告继续回答", has_report=True)
    assert intent.action == IntentAction.ANSWER_FROM_REPORT
    assert intent.target == IntentTarget.CURRENT_REPORT


def test_low_confidence_report_intent_is_clarified() -> None:
    intent = ChatIntent(
        action=IntentAction.CREATE_RESEARCH_REPORT,
        target=IntentTarget.NEW_TOPIC,
        rewritten_query="帮我做一下",
        confidence=0.6,
    )
    decision = apply_intent_policy(
        intent,
        has_report=True,
        report_creation_available=True,
        confidence_threshold=0.75,
    )

    assert decision.action == "clarify"
    assert decision.allow_report_side_effect is False


@pytest.mark.parametrize(
    ("permission_granted", "budget_available", "reason"),
    [
        (False, True, "report_creation_not_authorized"),
        (True, False, "report_budget_unavailable"),
    ],
)
def test_policy_blocks_report_when_guard_fails(
    permission_granted: bool,
    budget_available: bool,
    reason: str,
) -> None:
    intent = ChatIntent(
        action=IntentAction.CREATE_RESEARCH_REPORT,
        target=IntentTarget.NEW_TOPIC,
        rewritten_query="写一份 Redis 调研报告",
        confidence=0.95,
    )
    decision = apply_intent_policy(
        intent,
        has_report=False,
        report_creation_available=True,
        permission_granted=permission_granted,
        budget_available=budget_available,
    )

    assert decision.action == "clarify"
    assert decision.allow_report_side_effect is False
    assert decision.reason == reason


def test_intent_metrics_expose_confusion_and_false_creation_rate() -> None:
    metrics = build_intent_metrics(
        [
            {
                "expected_intent": "transform_report",
                "predicted_intent": "transform_report",
                "report_created": False,
            },
            {
                "expected_intent": "quick_search",
                "predicted_intent": "create_research_report",
                "report_created": False,
            },
            {
                "expected_intent": "normal_chat",
                "predicted_intent": "create_research_report",
                "report_created": True,
            },
            {
                "expected_intent": "create_research_report",
                "predicted_intent": "create_research_report",
                "report_created": True,
            },
        ]
    )

    assert metrics["confusion_matrix"]["quick_search"]["create_research_report"] == 1
    assert metrics["accuracy"] == 0.5
    assert metrics["report_route_false_positives"] == 2
    assert metrics["report_route_false_positive_rate"] == 0.6667
    assert metrics["false_report_creations"] == 1
    assert metrics["non_create_requests"] == 3
    assert metrics["false_report_creation_rate"] == 0.3333
    assert metrics["guarded_report_route_false_positives"] == 1
    assert metrics["report_creation_success_rate"] == 1.0


def test_false_creation_rate_uses_only_observed_side_effects() -> None:
    metrics = build_intent_metrics(
        [
            {
                "expected_intent": "quick_search",
                "predicted_intent": "quick_search",
            },
            {
                "expected_intent": "normal_chat",
                "predicted_intent": "normal_chat",
                "report_created": False,
            },
        ]
    )
    assert metrics["non_create_requests"] == 2
    assert metrics["non_create_requests_with_side_effect_observation"] == 1
    assert metrics["false_report_creation_rate"] == 0.0


@pytest.mark.asyncio
async def test_selected_quick_search_executes_exactly_once(monkeypatch) -> None:
    from chat.chat import ChatAgentWithMemory

    calls: list[str] = []
    agent = ChatAgentWithMemory.__new__(ChatAgentWithMemory)
    agent.config = type(
        "ConfigStub",
        (),
        {
            "smart_llm_model": "answer-model",
            "smart_llm_provider": "test",
            "llm_kwargs": {},
        },
    )()
    agent.search_metadata = None

    def quick_search(query: str) -> dict:
        calls.append(query)
        agent.search_metadata = {"query": query, "sources": [{"title": "Redis"}]}
        return {"results": [{"title": "Redis", "content": "stable release"}]}

    async def answer_completion(**kwargs) -> str:
        assert "Search evidence" in kwargs["messages"][-1]["content"]
        return "根据检索结果回答"

    agent.quick_search = quick_search
    monkeypatch.setattr("chat.chat.create_chat_completion", answer_completion)

    response, metadata = await agent.process_chat_completion(
        [{"role": "user", "content": "搜索 Redis 最新版本"}],
        allow_report_creation=False,
        forced_quick_search_query="搜索 Redis 最新版本",
    )

    assert response == "根据检索结果回答"
    assert calls == ["搜索 Redis 最新版本"]
    assert metadata[0]["tool"] == "quick_search"
