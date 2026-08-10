"""Cheap fuzz eval: noisy / underspecified chat inputs (no live LLM). :-)"""

from __future__ import annotations

import argparse
import asyncio
import os
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
    r"(写(?:一份)?(?:调研)?报告|调研报告|生成报告|帮我写报告|写个报告|"
    r"调研|create[_\s-]?report)",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(
    r"(查一下|搜索|最新|现在|什么版本|多少钱|新闻)",
    re.IGNORECASE,
)


def _ensure_clarify_env() -> None:
    os.environ.setdefault("RESEARCH_USER_PLANNING_CONTEXT", "true")
    os.environ.setdefault("RESEARCH_INTENT_CLARIFY", "true")
    os.environ.setdefault("RESEARCH_AMBIGUITY_PREFERENCE", "tech")


async def _resolve_intent(user_text: str) -> dict:
    from jobs.planning_context import resolve_report_intent

    return await resolve_report_intent(
        task=user_text,
        user_id="eval-fuzz",
        report_store=None,
        client_messages=[],
    )


def _mock_tools(user_text: str, intent: dict | None) -> list[str]:
    if intent and intent.get("action") == "clarify":
        return []
    text = user_text or ""
    # Explicit negation should never open a report. :-)
    if re.search(r"(别|不要|先别).{0,6}(写|生成|开).{0,4}报告", text):
        if _SEARCH_RE.search(text):
            return ["quick_search"]
        return []
    # ASR noise often mangles 调研 → 调演; treat both as report-ish only when
    # intent already proceeded. If clarify, tools stay empty above. :-)
    if intent and intent.get("action") == "proceed" and _REPORT_RE.search(text):
        return ["create_research_report"]
    if _SEARCH_RE.search(text):
        return ["quick_search"]
    return []


def _reply_blob(intent: dict | None) -> str:
    if not intent:
        return ""
    parts = [
        str(intent.get("clarification_question") or ""),
        str(intent.get("expanded_task") or ""),
        " ".join(str(x) for x in (intent.get("ambiguous_tokens") or [])),
    ]
    for opt in intent.get("options") or []:
        parts.append(str(opt.get("label") or ""))
        parts.append(str(opt.get("resolved_task") or ""))
    return "\n".join(parts)


async def run_case(case: dict) -> dict:
    case_id = case["id"]
    if (case.get("status") or "").lower() == "blocked":
        return {
            "id": case_id,
            "skipped": True,
            "reason": case.get("reason") or "blocked",
        }

    user_text = str(case.get("user") or "")
    expect = case.get("expect") or {}
    failures: list[str] = []

    intent = await _resolve_intent(user_text)
    tools = _mock_tools(user_text, intent)
    blob = _reply_blob(intent)

    if "intent_action" in expect:
        got = intent.get("action")
        if got != expect["intent_action"]:
            failures.append(
                f"intent_action expected={expect['intent_action']} got={got}"
            )

    if expect.get("no_tools") and tools:
        failures.append(f"expected no tools, got={tools}")

    for tool in expect.get("forbid_tools") or []:
        if tool in tools:
            failures.append(f"forbidden tool called: {tool}")

    if expect.get("ask_clarify") and intent.get("action") != "clarify":
        failures.append(f"ask_clarify expected clarify, got={intent.get('action')}")

    needles = expect.get("must_include_any") or expect.get("intent_guess_any") or []
    if needles and not any(str(n).lower() in blob.lower() for n in needles):
        failures.append(f"intent/reply missing any of {needles}")

    return {
        "id": case_id,
        "passed": len(failures) == 0,
        "failures": failures,
        "tools": tools,
        "intent_action": intent.get("action"),
        "reply_preview": blob[:160],
    }


async def main_async(args: argparse.Namespace) -> int:
    _ensure_clarify_env()
    cases_path = Path(__file__).parent / "cases.jsonl"
    cases = load_jsonl(cases_path, suite=args.suite, only_id=args.only)
    results = [await run_case(c) for c in cases]
    # Also surface blocked cases as skips for summary visibility. :-)
    if args.include_blocked:
        blocked = load_jsonl(
            cases_path, suite=args.suite, include_blocked=True, only_id=args.only
        )
        seen = {r["id"] for r in results}
        for case in blocked:
            if case["id"] not in seen and (case.get("status") or "").lower() == "blocked":
                results.append(await run_case(case))

    summary = summarize(results, pillar="fuzz", suite=args.suite)
    print_summary(summary)

    # Systematic recycle: failed cases → weaknesses.jsonl → promote later. :-)
    from record_weakness import record_weaknesses

    cases_by_id = {str(c.get("id")): c for c in cases}
    added = record_weaknesses(results, cases_by_id=cases_by_id)
    if added:
        print(f"Recorded {added} fuzz weakness(es) → evals/fuzz_eval/weaknesses.jsonl")

    return 0 if summary["ok"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuzz eval (cheap, offline)")
    parser.add_argument("--suite", default="cheap", choices=["cheap", "full", "nightly"])
    parser.add_argument("--only", default=None, help="Run a single case id")
    parser.add_argument(
        "--include-blocked",
        action="store_true",
        help="Also list blocked cases as SKIP",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
