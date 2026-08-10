"""Cheap dialogue eval: intent clarify + tool policy mocks (no live LLM). :-)"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "evals") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "evals"))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from _common import load_jsonl, print_summary, summarize  # noqa: E402


_REPORT_RE = re.compile(
    r"(写(?:一份)?(?:调研)?报告|调研报告|生成报告|帮我写报告|写个报告|create[_\s-]?report)",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(
    r"(查一下|搜索|最新|现在|什么版本|多少钱|新闻)",
    re.IGNORECASE,
)
_REFUSE_RE = re.compile(
    r"(入侵|窃取|黑客攻击|制作炸弹|违法犯罪)",
    re.IGNORECASE,
)


def _latest_user(turns: list[dict]) -> str:
    for t in reversed(turns or []):
        if t.get("role") == "user":
            return str(t.get("content") or "")
    return ""


async def _mock_intent(user_text: str) -> dict:
    from jobs.planning_context import resolve_report_intent

    return await resolve_report_intent(
        task=user_text,
        user_id="eval-dialogue",
        report_store=None,
        client_messages=[],
    )


def _mock_tools_for_utterance(user_text: str, intent: dict | None) -> list[str]:
    if _REFUSE_RE.search(user_text or ""):
        return []
    if intent and intent.get("action") == "clarify":
        return []
    if _REPORT_RE.search(user_text or ""):
        return ["create_research_report"]
    if _SEARCH_RE.search(user_text or ""):
        return ["quick_search"]
    return []


def _mock_reply(user_text: str, intent: dict | None, tools: list[str]) -> str:
    if _REFUSE_RE.search(user_text or ""):
        return "抱歉，我不能协助入侵或窃取数据等违法用途。"
    if intent and intent.get("action") == "clarify":
        return intent.get("clarification_question") or "请确认你指的是哪一个含义？"
    if "create_research_report" in tools:
        return "已为你提交独立报告任务。"
    if "quick_search" in tools:
        return "我来帮你检索一下公开资料。"
    return "好的，我在。"


async def run_case(case: dict) -> dict:
    case_id = case["id"]
    if (case.get("status") or "").lower() == "blocked":
        return {"id": case_id, "skipped": True, "reason": case.get("reason") or "blocked"}

    turns = case.get("turns") or []
    user_text = _latest_user(turns)
    expect = case.get("expect") or {}
    failures: list[str] = []

    intent = None
    if "intent_action" in expect or "must_include_any" in expect:
        intent = await _mock_intent(user_text)

    tools = _mock_tools_for_utterance(user_text, intent)
    reply = _mock_reply(user_text, intent, tools)

    if "intent_action" in expect:
        got = (intent or {}).get("action")
        if got != expect["intent_action"]:
            failures.append(f"intent_action expected={expect['intent_action']} got={got}")

    for tool in expect.get("must_tools") or []:
        if tool not in tools:
            failures.append(f"missing tool {tool}")

    for tool in expect.get("forbid_tools") or []:
        if tool in tools:
            failures.append(f"forbidden tool called: {tool}")

    allow = expect.get("allow_tools")
    if allow is not None:
        for tool in tools:
            if tool not in allow:
                failures.append(f"tool {tool} not in allow_tools={allow}")

    if expect.get("tool_task_contains") and "create_research_report" in tools:
        for needle in expect["tool_task_contains"]:
            if needle.lower() not in user_text.lower():
                failures.append(f"task text missing '{needle}'")

    if expect.get("refuse"):
        if "不能" not in reply and "无法" not in reply and "抱歉" not in reply:
            failures.append("expected refusal language")
        if tools:
            failures.append(f"refusal should not call tools, got={tools}")

    needles = expect.get("must_include_any") or []
    if needles and not any(n.lower() in reply.lower() for n in needles):
        failures.append(f"reply missing any of {needles}")

    return {
        "id": case_id,
        "passed": len(failures) == 0,
        "failures": failures,
        "tools": tools,
        "intent_action": (intent or {}).get("action"),
        "reply_preview": reply[:160],
    }


async def main_async(args: argparse.Namespace) -> int:
    cases_path = Path(__file__).parent / "cases.jsonl"
    cases = load_jsonl(cases_path, suite=args.suite, only_id=args.only)
    results = [await run_case(c) for c in cases]
    # Also surface blocked count for visibility
    all_cases = load_jsonl(
        cases_path, suite=args.suite, only_id=args.only, include_blocked=True
    )
    for c in all_cases:
        if (c.get("status") or "").lower() == "blocked":
            if args.only and c.get("id") != args.only:
                continue
            results.append(
                {
                    "id": c["id"],
                    "skipped": True,
                    "reason": c.get("reason") or "blocked",
                }
            )
    summary = summarize(results, pillar="dialogue", suite=args.suite)
    print_summary(summary)
    return 0 if summary["ok"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Dialogue eval (cheap mock)")
    parser.add_argument("--suite", default="cheap", choices=["cheap", "full", "nightly"])
    parser.add_argument("--only", default=None)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
