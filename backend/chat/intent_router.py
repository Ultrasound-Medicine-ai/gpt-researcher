"""Structured chat intent routing with conservative side-effect policy.

The LLM understands semantics and returns a validated route.  The policy layer
does not infer natural language intent; it only checks confidence, target/state,
feature availability, and whether a side effect may be requested.  Actual Job
permission, concurrency, idempotency, and daily-budget gates remain authoritative
in ``POST /api/jobs/research``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class IntentAction(str, Enum):
    ANSWER_FROM_REPORT = "answer_from_report"
    TRANSFORM_REPORT = "transform_report"
    QUICK_SEARCH = "quick_search"
    CREATE_RESEARCH_REPORT = "create_research_report"
    NORMAL_CHAT = "normal_chat"
    CLARIFY = "clarify"


class IntentTarget(str, Enum):
    CURRENT_REPORT = "current_report"
    NEW_TOPIC = "new_topic"
    WEB = "web"
    NONE = "none"
    UNKNOWN = "unknown"


class ChatIntent(BaseModel):
    """Provider-independent structured output from the intent router."""

    model_config = ConfigDict(extra="ignore")

    action: IntentAction
    target: IntentTarget
    rewritten_query: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    clarification_question: str = ""
    reason: str = ""
    source: Literal["llm", "dialogue_state", "fallback"] = "llm"


class PolicyDecision(BaseModel):
    """Deterministic decision consumed by the application layer."""

    action: Literal[
        "answer_in_chat",
        "quick_search",
        "request_report_creation",
        "clarify",
    ]
    allow_report_side_effect: bool = False
    query: str = ""
    message: str = ""
    reason: str = ""
    authorization_check: Literal[
        "passed", "denied", "deferred", "not_required"
    ] = "not_required"
    budget_check: Literal[
        "passed", "unavailable", "deferred", "not_required"
    ] = "not_required"


RouterCompletion = Callable[..., Awaitable[str]]


def intent_router_enabled() -> bool:
    return (os.getenv("CHAT_INTENT_ROUTER_ENABLED") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def intent_confidence_threshold() -> float:
    raw = (os.getenv("CHAT_INTENT_CONFIDENCE_THRESHOLD") or "0.75").strip()
    try:
        return min(1.0, max(0.0, float(raw)))
    except ValueError:
        return 0.75


def intent_router_timeout_sec() -> float:
    raw = (os.getenv("CHAT_INTENT_ROUTER_TIMEOUT_SEC") or "12").strip()
    try:
        return min(60.0, max(1.0, float(raw)))
    except ValueError:
        return 12.0


def _recent_history(messages: list[dict[str, Any]], limit: int = 6) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in list(messages or [])[-limit:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = " ".join(str(item.get("content") or "").split()).strip()
        if role in {"user", "assistant"} and content:
            out.append({"role": role, "content": content[:800]})
    return out


def _router_prompt(
    *,
    latest_message: str,
    has_report: bool,
    report_topic: str,
    messages: list[dict[str, Any]],
) -> list[dict[str, str]]:
    state = {
        "latest_message": latest_message[:2000],
        "has_current_report": bool(has_report),
        "current_report_topic": (report_topic or "")[:500],
        "recent_messages": _recent_history(messages),
    }
    system = """
You are an intent router for a research Agent product. Return exactly one JSON
object and no markdown. Do not answer the user and do not call tools.

Allowed action values:
- answer_from_report: answer a question using the current report.
- transform_report: summarize, translate, rewrite, extract, explain, or reshape
  the current report inside chat.
- quick_search: fresh external facts are required, without creating a report.
- create_research_report: the user clearly requests a separate new research Job.
- normal_chat: ordinary conversation that needs neither web search nor a Job.
- clarify: the target or requested side effect is ambiguous.

Allowed target values: current_report, new_topic, web, none, unknown.

Critical policy semantics:
- Referring to the current/previous report and asking to summarize, explain,
  translate, modify, extract, or continue it is NOT a new report.
- create_research_report requires a clear request for a separate/new report or
  research task. If unsure between current-report work and a new Job, clarify.
- A report Job costs searches/model calls, so prefer clarify over guessing.
- If the previous assistant asked the user to choose between continuing with
  the current report and creating a new report, treat the user's explicit
  choice "continue with/based on this report" as answer_from_report with
  target=current_report. Do not ask the same clarification again.
- confidence is your confidence in the action and target, from 0 to 1.

Return keys: action, target, rewritten_query, confidence,
clarification_question, reason.
""".strip()
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(state, ensure_ascii=False),
        },
    ]


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("intent router output must be a JSON object")
    return value


# These rules are deliberately narrow.  They run only when the semantic router
# is unavailable/invalid and must fail closed for report creation.
_CURRENT_REPORT_REF = re.compile(
    r"(?:这个|这份|当前|上述|上面(?:的)?|前面(?:的)?|刚才(?:的)?)报告",
    re.IGNORECASE,
)
_CURRENT_REPORT_OPERATION = re.compile(
    r"总结|概括|摘要|提炼|翻译|改写|润色|修改|解释|压缩|扩写|提取|列出|分析",
    re.IGNORECASE,
)
_CURRENT_REPORT_SELECTION = re.compile(
    r"(?:基于|根据|用)(?:这个|这份|当前|原有|已有)?报告(?:继续)?(?:回答|处理|分析)?"
    r"|(?:继续|就)(?:基于|根据|用)(?:这个|这份|当前)?报告"
    r"|continue\s+(?:with|using)\s+(?:this|the\s+current)\s+report",
    re.IGNORECASE,
)
_REPORT_CHOICE_QUESTION = re.compile(
    r"当前报告.{0,40}(?:新|创建).{0,30}报告"
    r"|(?:continue|current report).{0,80}(?:create|new report)",
    re.IGNORECASE,
)
_EXPLICIT_NEW_REPORT = re.compile(
    r"(?:新建|创建|另外|另写|重新调研|独立).{0,12}(?:报告|调研)"
    r"|(?:写|生成|撰写|提交)(?:一份|一篇|一个|个)?(?:关于)?.{0,80}(?:调研报告|研究报告)"
    r"|(?:写|生成|撰写)(?:一份|一篇|一个|个)?(?:关于)?.{0,20}(?:报告)(?:介绍|研究|分析)?.{1,80}"
    r"|(?:write|create|generate)\s+(?:a\s+)?(?:new\s+)?(?:research\s+)?report",
    re.IGNORECASE,
)
_EXPLICIT_SEARCH = re.compile(
    r"搜索|查一下|检索|最新|今天|近期|当前价格|多少钱|价格|什么版本|现在.{0,40}版本|(?:search|look\s+up)\b",
    re.IGNORECASE,
)

_REPORT_NEGATION = re.compile(
    r"(?:do\s+not|don't|dont|no|not)\s+(?:create|generate|write|start).*?report"
    r"|(?:不要|不用|别|別|不需要).{0,12}(?:创建|生成|写|做).{0,12}(?:报告|调研)",
    re.IGNORECASE,
)


def report_creation_allowed_by_text(latest_message: str) -> bool:
    """Fail closed for an expensive report Job when user wording is not explicit."""
    text = " ".join((latest_message or "").split()).strip()
    return not _REPORT_NEGATION.search(text) and bool(_EXPLICIT_NEW_REPORT.search(text))


def constrain_report_route(intent: ChatIntent, latest_message: str) -> ChatIntent:
    """Make a costly report route consistent with explicit user wording."""
    if intent.action != IntentAction.CREATE_RESEARCH_REPORT:
        return intent
    text = latest_message or ""
    if report_creation_allowed_by_text(text):
        return intent
    if _REPORT_NEGATION.search(text) and _EXPLICIT_SEARCH.search(text):
        return intent.model_copy(update={
            "action": IntentAction.QUICK_SEARCH,
            "target": IntentTarget.WEB,
            "confidence": 1.0,
            "reason": "negative_report_request_with_explicit_search",
            "source": "fallback",
        })
    return intent.model_copy(update={
        "action": IntentAction.CLARIFY,
        "target": IntentTarget.UNKNOWN,
        "confidence": 0.0,
        "reason": "report_request_not_explicit",
        "source": "fallback",
    })


def fallback_intent(
    latest_message: str,
    *,
    has_report: bool,
) -> ChatIntent:
    """Conservative no-LLM fallback; ambiguous inputs never create a Job."""
    text = " ".join((latest_message or "").split()).strip()
    if has_report and _CURRENT_REPORT_SELECTION.search(text):
        return ChatIntent(
            action=IntentAction.ANSWER_FROM_REPORT,
            target=IntentTarget.CURRENT_REPORT,
            rewritten_query=text,
            confidence=0.98,
            reason="explicit_current_report_selection",
            source="fallback",
        )
    if has_report and _CURRENT_REPORT_REF.search(text) and _CURRENT_REPORT_OPERATION.search(text):
        return ChatIntent(
            action=IntentAction.TRANSFORM_REPORT,
            target=IntentTarget.CURRENT_REPORT,
            rewritten_query=text,
            confidence=0.95,
            reason="explicit_current_report_operation",
            source="fallback",
        )
    if _EXPLICIT_NEW_REPORT.search(text):
        return ChatIntent(
            action=IntentAction.CREATE_RESEARCH_REPORT,
            target=IntentTarget.NEW_TOPIC,
            rewritten_query=text,
            confidence=0.9,
            reason="explicit_new_report_request",
            source="fallback",
        )
    if _EXPLICIT_SEARCH.search(text):
        return ChatIntent(
            action=IntentAction.QUICK_SEARCH,
            target=IntentTarget.WEB,
            rewritten_query=text,
            confidence=0.85,
            reason="explicit_web_search_request",
            source="fallback",
        )
    return ChatIntent(
        action=IntentAction.CLARIFY,
        target=IntentTarget.UNKNOWN,
        rewritten_query=text,
        confidence=0.0,
        clarification_question=(
            "你希望我基于当前报告继续回答，还是创建一份新的独立研究报告？"
            if has_report
            else "你希望我直接回答、搜索最新资料，还是创建一份独立研究报告？"
        ),
        reason="router_unavailable_fail_closed",
        source="fallback",
    )


def resolve_clarification_choice(
    latest_message: str,
    *,
    has_report: bool,
    messages: list[dict[str, Any]],
) -> ChatIntent | None:
    """Resolve an explicit answer to our immediately preceding report choice."""
    if not has_report or not _CURRENT_REPORT_SELECTION.search(latest_message or ""):
        return None

    previous_assistant = ""
    previous_user = ""
    seen_latest_user = False
    for item in reversed(messages or []):
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = " ".join(str(item.get("content") or "").split()).strip()
        if not content:
            continue
        if role == "user" and not seen_latest_user:
            seen_latest_user = True
            continue
        if role == "assistant" and not previous_assistant:
            previous_assistant = content
            continue
        if role == "user" and seen_latest_user:
            previous_user = content
            break

    if not _REPORT_CHOICE_QUESTION.search(previous_assistant):
        return None
    return ChatIntent(
        action=IntentAction.ANSWER_FROM_REPORT,
        target=IntentTarget.CURRENT_REPORT,
        rewritten_query=previous_user or latest_message.strip(),
        confidence=1.0,
        reason="resolved_previous_report_choice",
        source="dialogue_state",
    )


async def classify_chat_intent(
    *,
    latest_message: str,
    has_report: bool,
    report_topic: str,
    messages: list[dict[str, Any]],
    model: str,
    llm_provider: str,
    llm_kwargs: dict[str, Any] | None = None,
    completion: RouterCompletion | None = None,
) -> ChatIntent:
    """Run the structured semantic router, falling back conservatively."""
    resolved_choice = resolve_clarification_choice(
        latest_message,
        has_report=has_report,
        messages=messages,
    )
    if resolved_choice is not None:
        return resolved_choice

    if not intent_router_enabled():
        return fallback_intent(latest_message, has_report=has_report)

    if completion is None:
        from gpt_researcher.utils.llm import create_chat_completion

        completion = create_chat_completion

    prompt = _router_prompt(
        latest_message=latest_message,
        has_report=has_report,
        report_topic=report_topic,
        messages=messages,
    )
    try:
        raw = await asyncio.wait_for(
            completion(
                messages=prompt,
                model=model,
                temperature=0.0,
                max_tokens=400,
                llm_provider=llm_provider,
                llm_kwargs=llm_kwargs or {},
                reasoning_effort="low",
                allow_continue=False,
            ),
            timeout=intent_router_timeout_sec(),
        )
        payload = _extract_json_object(str(raw or ""))
        payload["source"] = "llm"
        intent = ChatIntent.model_validate(payload)
        if not intent.rewritten_query.strip():
            intent.rewritten_query = latest_message.strip()
        return constrain_report_route(intent, latest_message)
    except (TimeoutError, ValueError, TypeError, ValidationError, json.JSONDecodeError) as exc:
        logger.warning("Structured intent router failed closed: %s", exc)
    except Exception as exc:  # provider/network errors are non-fatal to chat
        logger.warning("Intent router unavailable; using conservative fallback: %s", exc)
    return fallback_intent(latest_message, has_report=has_report)


def apply_intent_policy(
    intent: ChatIntent,
    *,
    has_report: bool,
    report_creation_available: bool,
    permission_granted: bool | None = None,
    budget_available: bool | None = None,
    side_effects_allowed: bool = True,
    confidence_threshold: float | None = None,
) -> PolicyDecision:
    """Validate state/confidence before the application requests a side effect."""
    threshold = (
        intent_confidence_threshold()
        if confidence_threshold is None
        else min(1.0, max(0.0, float(confidence_threshold)))
    )
    if intent.confidence < threshold or intent.action == IntentAction.CLARIFY:
        return PolicyDecision(
            action="clarify",
            message=intent.clarification_question
            or (
                "你希望我基于当前报告继续回答，还是创建一份新的独立研究报告？"
                if has_report
                else "请说明你希望直接回答、搜索资料，还是创建独立研究报告。"
            ),
            reason="low_confidence_or_clarify",
        )

    if intent.action in {
        IntentAction.ANSWER_FROM_REPORT,
        IntentAction.TRANSFORM_REPORT,
    }:
        if not has_report or intent.target != IntentTarget.CURRENT_REPORT:
            return PolicyDecision(
                action="clarify",
                message="当前会话中没有可处理的报告，请说明目标内容。",
                reason="current_report_target_unavailable",
            )
        return PolicyDecision(
            action="answer_in_chat",
            query=intent.rewritten_query,
            reason="current_report_operation",
        )

    if intent.action == IntentAction.CREATE_RESEARCH_REPORT:
        if intent.target != IntentTarget.NEW_TOPIC:
            return PolicyDecision(
                action="clarify",
                message="你希望在当前对话中处理，还是创建一份新的独立研究报告？",
                reason="report_target_not_new",
            )
        if not report_creation_available:
            return PolicyDecision(
                action="clarify",
                message="当前无法创建独立报告，我可以先在对话中帮助你梳理需求。",
                reason="report_creation_unavailable",
            )
        if permission_granted is False:
            return PolicyDecision(
                action="clarify",
                message="当前身份没有创建独立报告的权限。",
                reason="report_creation_not_authorized",
                authorization_check="denied",
            )
        if budget_available is False:
            return PolicyDecision(
                action="clarify",
                message="当前研究预算不足，暂时不能创建新的独立报告。",
                reason="report_budget_unavailable",
                authorization_check=(
                    "passed" if permission_granted is True else "deferred"
                ),
                budget_check="unavailable",
            )
        if not side_effects_allowed:
            return PolicyDecision(
                action="clarify",
                message="当前请求不允许触发创建报告的副作用。",
                reason="report_side_effect_disallowed",
                authorization_check=(
                    "passed" if permission_granted is True else "deferred"
                ),
                budget_check=("passed" if budget_available is True else "deferred"),
            )
        return PolicyDecision(
            action="request_report_creation",
            allow_report_side_effect=True,
            query=intent.rewritten_query,
            reason="high_confidence_new_report",
            authorization_check=(
                "passed" if permission_granted is True else "deferred"
            ),
            budget_check="passed" if budget_available is True else "deferred",
        )

    if intent.action == IntentAction.QUICK_SEARCH:
        return PolicyDecision(
            action="quick_search",
            query=intent.rewritten_query,
            reason="fresh_web_information",
        )

    return PolicyDecision(
        action="answer_in_chat",
        query=intent.rewritten_query,
        reason="normal_chat",
    )


def route_metadata(intent: ChatIntent, decision: PolicyDecision) -> dict[str, Any]:
    return {
        "intent_route": intent.model_dump(mode="json"),
        "intent_policy": decision.model_dump(mode="json"),
    }
