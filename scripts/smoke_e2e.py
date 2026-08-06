#!/usr/bin/env python3
"""GPT Researcher smoke / E2E checks.

Quick mode: API + UI reachability, chat endpoint, optional unit tests.
Full mode: WebSocket research (same path as Next.js UI) + chat + report quality.

Usage:
  python scripts/smoke_e2e.py --mode quick
  python scripts/smoke_e2e.py --mode full --timeout 600
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _http_get(url: str, timeout: float = 15.0) -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": "gpt-researcher-smoke/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body


def _http_post_json(url: str, payload: dict, timeout: float = 120.0) -> tuple[int, dict]:
    import httpx

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        return resp.status_code, data


def analyze_report_quality(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    headings = re.findall(r"^#{1,3}\s+.+", text, flags=re.MULTILINE)
    links = re.findall(r"https?://[^\s\)\]>]+", text)
    bracket_cites = re.findall(r"\[\d+\]", text)
    words = text.split()

    checks = {
        "non_empty": len(text) > 0,
        "min_length_300": len(text) >= 300,
        "min_words_80": len(words) >= 80,
        "has_headings": len(headings) >= 1,
        "has_links_or_citations": len(links) >= 1 or len(bracket_cites) >= 1,
    }

    score = sum(1 for ok in checks.values() if ok)
    grade = "PASS" if all(checks[k] for k in ("non_empty", "min_length_300")) else "WARN"
    if not checks["non_empty"]:
        grade = "FAIL"

    return {
        "char_count": len(text),
        "word_count": len(words),
        "heading_count": len(headings),
        "link_count": len(links),
        "bracket_citation_count": len(bracket_cites),
        "checks": checks,
        "quality_score": f"{score}/{len(checks)}",
        "grade": grade,
        "preview": text[:500] + ("..." if len(text) > 500 else ""),
    }


def check_api_root(api_url: str) -> dict[str, Any]:
    status, body = _http_get(f"{api_url.rstrip('/')}/")
    data = json.loads(body)
    ok = status == 200 and data.get("service") == "GPT Researcher API"
    return {
        "name": "api_root",
        "ok": ok,
        "status": status,
        "body": data,
    }


def check_api_docs(api_url: str) -> dict[str, Any]:
    status, _ = _http_get(f"{api_url.rstrip('/')}/docs", timeout=20.0)
    return {"name": "api_docs", "ok": status == 200, "status": status}


def check_ui(ui_url: str) -> dict[str, Any]:
    try:
        status, body = _http_get(ui_url.rstrip("/") + "/", timeout=20.0)
        ok = status == 200 and len(body) > 100
        return {"name": "nextjs_ui", "ok": ok, "status": status, "url": ui_url}
    except URLError as exc:
        return {"name": "nextjs_ui", "ok": False, "error": str(exc), "url": ui_url}


def check_chat(api_url: str) -> dict[str, Any]:
    sample_report = (
        "# Smoke Test Report\n\n"
        "CRISPR is a genome editing technology derived from bacterial immune systems.\n"
        "Source: https://example.com/crispr-overview\n"
    )
    payload = {
        "report": sample_report,
        "messages": [
            {
                "role": "user",
                "content": "用一句话总结这篇报告的核心观点。",
            }
        ],
    }
    status, data = _http_post_json(
        f"{api_url.rstrip('/')}/api/chat",
        payload,
        timeout=180.0,
    )
    response = data.get("response") or {}
    content = (response.get("content") or "").strip()
    ok = status == 200 and bool(content) and "error" not in data
    return {
        "name": "chat_api",
        "ok": ok,
        "status": status,
        "response_chars": len(content),
        "tool_calls": (response.get("metadata") or {}).get("tool_calls"),
        "preview": content[:200],
        "error": data.get("error"),
    }


async def run_websocket_research(
    api_url: str,
    query: str,
    timeout: float,
) -> dict[str, Any]:
    import websockets

    ws_base = api_url.rstrip("/").replace("https://", "wss://").replace("http://", "ws://")
    ws_uri = f"{ws_base}/ws"

    payload = {
        "task": query,
        "report_type": "research_report",
        "report_source": "web",
        "tone": "Objective",
        "query_domains": [],
        "mcp_enabled": False,
        "mcp_strategy": "fast",
        "mcp_configs": [],
    }
    start_msg = f"start {json.dumps(payload)}"

    report_text = ""
    path_msg = None
    errors: list[str] = []
    started = time.time()

    async with websockets.connect(ws_uri, open_timeout=30) as ws:
        await ws.send(start_msg)

        while time.time() - started < timeout:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(60.0, timeout))
            except asyncio.TimeoutError:
                continue

            if raw == "pong":
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if isinstance(data, dict):
                if data.get("type") == "path":
                    path_msg = data
                    break
                if "report" in data and isinstance(data["report"], str):
                    if len(data["report"]) > len(report_text):
                        report_text = data["report"]
                if data.get("type") == "error" or data.get("error"):
                    errors.append(str(data.get("error") or data))

        if not path_msg and report_text:
            pass
        elif path_msg and not report_text:
            output = path_msg.get("output") or {}
            md_path = output.get("markdown") or output.get("md")
            if md_path and os.path.isfile(md_path):
                report_text = Path(md_path).read_text(encoding="utf-8", errors="replace")

    elapsed = round(time.time() - started, 1)
    ok = len(report_text.strip()) >= 300 and not errors
    return {
        "name": "websocket_research",
        "ok": ok,
        "elapsed_sec": elapsed,
        "report": report_text,
        "path_message": path_msg,
        "errors": errors,
        "query": query,
    }


def save_artifacts(output_dir: Path, report: str, quality: dict, results: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.md").write_text(report or "", encoding="utf-8")
    (output_dir / "quality.json").write_text(
        json.dumps(quality, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    summary_lines = [
        f"Smoke run: {datetime.now().isoformat(timespec='seconds')}",
        f"Report grade: {quality.get('grade')} ({quality.get('quality_score')})",
        f"Chars: {quality.get('char_count')} | Words: {quality.get('word_count')}",
        f"Headings: {quality.get('heading_count')} | Links: {quality.get('link_count')}",
        "",
        "Checks:",
    ]
    for key, val in (quality.get("checks") or {}).items():
        summary_lines.append(f"  - {key}: {'OK' if val else 'FAIL'}")
    summary_lines.extend(["", "Steps:"])
    for item in results:
        mark = "OK" if item.get("ok") else "FAIL"
        summary_lines.append(f"  [{mark}] {item.get('name')}")
    (output_dir / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")


def print_results(results: list[dict], output_dir: Path | None) -> int:
    failed = [r for r in results if not r.get("ok")]
    print("\n=== GPT Researcher Smoke Check ===\n")
    for item in results:
        mark = "PASS" if item.get("ok") else "FAIL"
        extra = ""
        if item.get("name") == "websocket_research":
            extra = f" ({item.get('elapsed_sec')}s, {len((item.get('report') or ''))} chars)"
        elif item.get("name") == "chat_api":
            extra = f" ({item.get('response_chars', 0)} chars)"
        elif item.get("name") == "report_quality":
            extra = f" (grade={item.get('grade')}, score={item.get('quality_score')})"
        print(f"  [{mark}] {item.get('name')}{extra}")
        if not item.get("ok"):
            for key in ("error", "errors", "status"):
                if item.get(key):
                    print(f"         {key}: {item[key]}")

    if output_dir:
        print(f"\nArtifacts: {output_dir}")
        print(f"  - report.md      (full report for quality review)")
        print(f"  - summary.txt    (human-readable summary)")
        print(f"  - quality.json   (metrics)")

    if failed:
        print(f"\nFAILED: {len(failed)} check(s). Fix before committing.")
        return 1

    print("\nAll checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GPT Researcher smoke / E2E checks")
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--api-url", default=os.getenv("SMOKE_API_URL", "http://localhost:8000"))
    parser.add_argument("--ui-url", default=os.getenv("SMOKE_UI_URL", "http://localhost:3000"))
    parser.add_argument(
        "--query",
        default="Briefly explain what CRISPR is and one major application.",
        help="Research question for full-mode WebSocket test",
    )
    parser.add_argument("--timeout", type=float, default=600.0, help="WebSocket research timeout (seconds)")
    parser.add_argument("--output-dir", default="", help="Directory for report artifacts (auto-created in full mode)")
    parser.add_argument("--skip-ui", action="store_true", help="Skip Next.js HTTP check")
    args = parser.parse_args()

    os.chdir(ROOT)

    results: list[dict] = []
    output_dir: Path | None = None
    report_for_quality = ""

    # Always check services first
    for fn in (lambda: check_api_root(args.api_url), lambda: check_api_docs(args.api_url)):
        try:
            results.append(fn())
        except Exception as exc:
            results.append({"name": fn.__name__, "ok": False, "error": str(exc)})

    if not args.skip_ui:
        results.append(check_ui(args.ui_url))
    else:
        results.append({"name": "nextjs_ui", "ok": True, "skipped": True})

    if args.mode == "quick":
        try:
            results.append(check_chat(args.api_url))
        except Exception as exc:
            results.append({"name": "chat_api", "ok": False, "error": str(exc)})
    else:
        try:
            ws_result = asyncio.run(
                run_websocket_research(args.api_url, args.query, args.timeout)
            )
            report_for_quality = ws_result.pop("report", "") or ""
            results.append(ws_result)

            quality = analyze_report_quality(report_for_quality)
            quality_result = {
                "name": "report_quality",
                "ok": quality["grade"] != "FAIL",
                **quality,
            }
            results.append(quality_result)

            try:
                chat_result = check_chat(args.api_url)
                if report_for_quality:
                    status, data = _http_post_json(
                        f"{args.api_url.rstrip('/')}/api/chat",
                        {
                            "report": report_for_quality,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "列出本报告的三个要点，并说明是否引用了外部来源。",
                                }
                            ],
                        },
                        timeout=180.0,
                    )
                    content = ((data.get("response") or {}).get("content") or "").strip()
                    chat_on_report = {
                        "name": "chat_on_report",
                        "ok": status == 200 and len(content) > 20,
                        "status": status,
                        "response_chars": len(content),
                        "preview": content[:200],
                    }
                    results.append(chat_on_report)
                else:
                    results.append(chat_result)
            except Exception as exc:
                results.append({"name": "chat_on_report", "ok": False, "error": str(exc)})

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(args.output_dir) if args.output_dir else ROOT / "outputs" / "smoke" / stamp
            save_artifacts(output_dir, report_for_quality, quality, results)
        except Exception as exc:
            results.append({"name": "websocket_research", "ok": False, "error": str(exc)})

    return print_results(results, output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
