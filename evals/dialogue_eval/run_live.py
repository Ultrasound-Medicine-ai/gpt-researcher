"""Live Chat eval against running API (/api/chat). :-)

Requires:
  - API up (default http://127.0.0.1:8000)
  - LLM keys configured in server env

Usage:
  python evals/dialogue_eval/run_live.py --limit 3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "evals") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "evals"))

from _common import print_summary, summarize  # noqa: E402

DEFAULT_BASE = "http://127.0.0.1:8000"


def _http_json(url: str, *, data: dict | None = None, headers: dict | None = None, timeout: int = 120) -> tuple[int, dict, dict]:
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="GET" if data is None else "POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            cookie = resp.headers.get("Set-Cookie") or ""
            payload = json.loads(raw) if raw else {}
            return resp.status, payload, {"set_cookie": cookie}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": raw[:500]}
        return exc.code, payload, {}


def bootstrap_cookie(base: str) -> str:
    code, _, meta = _http_json(f"{base.rstrip('/')}/api/auth/me", timeout=30)
    if code >= 400:
        return ""
    # Prefer cookie jar from set-cookie; urllib doesn't persist — parse visitor cookie if present
    set_cookie = meta.get("set_cookie") or ""
    parts = []
    for chunk in set_cookie.split(","):
        # naive: take first name=value
        nv = chunk.split(";", 1)[0].strip()
        if "=" in nv:
            parts.append(nv)
    return "; ".join(parts)


def run_case(base: str, case: dict, cookie: str) -> dict:
    case_id = case["id"]
    if (case.get("status") or "").lower() == "blocked":
        return {"id": case_id, "skipped": True, "reason": case.get("reason") or "blocked"}

    user = str(case.get("user") or "").strip()
    expect = case.get("expect") or {}
    headers = {}
    if cookie:
        headers["Cookie"] = cookie

    t0 = time.time()
    code, payload, _ = _http_json(
        f"{base.rstrip('/')}/api/chat",
        data={
            "report": "",
            "messages": [{"role": "user", "content": user}],
            "research_topic": "",
            "research_context": "",
            "report_language": "chinese",
        },
        headers=headers,
        timeout=180,
    )
    elapsed = round(time.time() - t0, 2)
    failures: list[str] = []

    if code >= 400:
        return {
            "id": case_id,
            "passed": False,
            "failures": [f"HTTP {code}: {payload}"],
            "elapsed_sec": elapsed,
        }

    response = payload.get("response") or {}
    content = str(response.get("content") or "")
    meta = response.get("metadata") or payload.get("metadata") or {}
    tool_calls = meta.get("tool_calls") if isinstance(meta, dict) else []
    if not isinstance(tool_calls, list):
        tool_calls = []

    tools = [str(t.get("tool") or "") for t in tool_calls if isinstance(t, dict)]

    if expect.get("tool"):
        if expect["tool"] not in tools:
            # Also accept forced report_request metadata
            if expect["tool"] == "create_research_report" and meta.get("report_request"):
                pass
            else:
                failures.append(f"expected tool {expect['tool']} got={tools}")

    if expect.get("forbid_tool") and expect["forbid_tool"] in tools:
        failures.append(f"forbidden tool {expect['forbid_tool']}")

    if expect.get("task_contains_any") and "create_research_report" in tools:
        task_blob = " ".join(
            str(t.get("task") or "") for t in tool_calls if isinstance(t, dict)
        )
        if not any(x.lower() in task_blob.lower() for x in expect["task_contains_any"]):
            failures.append("report task missing expected keywords")

    if expect.get("clarify_or_report"):
        needles = expect.get("must_include_any") or []
        ok_text = any(n.lower() in content.lower() for n in needles) if needles else False
        ok_tool = "create_research_report" in tools or bool(meta.get("report_request"))
        if not (ok_text or ok_tool):
            failures.append("expected clarify text or report tool")

    min_chars = int(expect.get("min_reply_chars") or 0)
    if min_chars and len(content.strip()) < min_chars:
        failures.append(f"reply too short (<{min_chars})")

    return {
        "id": case_id,
        "passed": len(failures) == 0,
        "failures": failures,
        "elapsed_sec": elapsed,
        "tools": tools,
        "reply_preview": content[:200],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Live chat eval")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--cases", default=str(Path(__file__).parent / "live_cases.jsonl"))
    args = parser.parse_args()

    # Health check
    try:
        code, _, _ = _http_json(f"{args.base_url.rstrip('/')}/", timeout=10)
    except Exception as exc:  # noqa: BLE001
        print(f"API unreachable at {args.base_url}: {exc}")
        raise SystemExit(2)

    cookie = bootstrap_cookie(args.base_url)
    cases: list[dict] = []
    with open(args.cases, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if (case.get("status") or "active").lower() == "blocked":
                continue
            cases.append(case)
            if len(cases) >= args.limit:
                break

    results = [run_case(args.base_url, c, cookie) for c in cases]
    summary = summarize(results, pillar="dialogue_live", suite="full")
    print_summary(summary)

    out_dir = REPO_ROOT / "evals" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "live_chat_latest.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
