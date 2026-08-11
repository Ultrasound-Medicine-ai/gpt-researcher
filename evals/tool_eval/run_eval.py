"""Cheap tool-chain eval: selection + arg contracts + timeout degrade mock. :-)"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "evals") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "evals"))

from _common import load_jsonl, print_summary, summarize  # noqa: E402


_REPORT_RE = re.compile(
    r"(写(?:一份)?(?:调研)?报告|调研报告|生成报告|帮我写报告|写个报告)",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(
    r"(查一下|搜索|检索|什么是|新闻|多少钱|最新版|是什么)",
    re.IGNORECASE,
)
_CHITCHAT_RE = re.compile(r"^(你好|您好|hi|hello|你是谁)", re.IGNORECASE)


def mock_select_tool(user: str) -> tuple[str | None, dict]:
    text = (user or "").strip()
    if not text or _CHITCHAT_RE.search(text):
        return None, {}
    if _REPORT_RE.search(text):
        return "create_research_report", {"task": text, "requirements": ""}
    if _SEARCH_RE.search(text):
        return "quick_search", {"query": text}
    return None, {}


def mock_execute(tool: str | None, args: dict, inject: dict | None) -> dict:
    inject = inject or {}
    if tool == "quick_search" and inject.get("quick_search_error"):
        err = str(inject["quick_search_error"])
        return {
            "ok": False,
            "degraded": True,
            "reply": f"搜索暂时超时（{err}），请稍后再试。",
        }
    if tool == "create_research_report":
        return {"ok": True, "degraded": False, "reply": "报告任务已创建。"}
    if tool == "quick_search":
        return {"ok": True, "degraded": False, "reply": "已检索到若干公开来源。"}
    return {"ok": True, "degraded": False, "reply": "好的。"}


def run_case(case: dict) -> dict:
    case_id = case["id"]
    if (case.get("status") or "").lower() == "blocked":
        return {"id": case_id, "skipped": True, "reason": case.get("reason") or "blocked"}

    user = str(case.get("user") or "")
    expect = case.get("expect") or {}
    inject = case.get("inject") or {}
    failures: list[str] = []

    tool, args = mock_select_tool(user)
    exec_result = mock_execute(tool, args, inject)

    expected_tool = expect.get("selected_tool", "__missing__")
    if "selected_tool" in expect and tool != expect.get("selected_tool"):
        failures.append(f"selected_tool expected={expect.get('selected_tool')} got={tool}")

    for key in expect.get("args_required") or []:
        if not str(args.get(key) or "").strip():
            failures.append(f"missing arg {key}")

    if expect.get("task_must_match") and tool == "create_research_report":
        if not re.search(expect["task_must_match"], str(args.get("task") or "")):
            failures.append("task_must_match failed")

    if expect.get("query_must_match") and tool == "quick_search":
        if not re.search(expect["query_must_match"], str(args.get("query") or "")):
            failures.append("query_must_match failed")

    for forbidden in expect.get("forbid_tools") or []:
        if tool == forbidden:
            failures.append(f"forbidden tool {forbidden}")

    if "degraded" in expect and bool(exec_result.get("degraded")) != bool(expect["degraded"]):
        failures.append(
            f"degraded expected={expect['degraded']} got={exec_result.get('degraded')}"
        )

    needles = expect.get("must_include_any") or []
    reply = str(exec_result.get("reply") or "")
    if needles and not any(n.lower() in reply.lower() for n in needles):
        failures.append(f"reply missing any of {needles}")

    # silence unused when selected_tool key absent
    _ = expected_tool

    return {
        "id": case_id,
        "passed": len(failures) == 0,
        "failures": failures,
        "selected_tool": tool,
        "args": args,
        "degraded": exec_result.get("degraded"),
        "reply_preview": reply[:160],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool eval (cheap mock)")
    parser.add_argument("--suite", default="cheap", choices=["cheap", "full", "nightly"])
    parser.add_argument("--only", default=None)
    args = parser.parse_args()

    cases_path = Path(__file__).parent / "cases.jsonl"
    cases = load_jsonl(cases_path, suite=args.suite, only_id=args.only)
    results = [run_case(c) for c in cases]
    all_cases = load_jsonl(
        cases_path, suite=args.suite, only_id=args.only, include_blocked=True
    )
    for c in all_cases:
        if (c.get("status") or "").lower() == "blocked":
            if args.only and c.get("id") != args.only:
                continue
            results.append(
                {"id": c["id"], "skipped": True, "reason": c.get("reason") or "blocked"}
            )

    summary = summarize(results, pillar="tool", suite=args.suite)
    print_summary(summary)
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
