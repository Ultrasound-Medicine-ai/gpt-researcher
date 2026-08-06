#!/usr/bin/env python3
"""Inspect GPT Researcher pipeline stats: search volume, context size, model input estimates.

Modes:
  summary   Parse latest outputs/*.json + logs/app.log (default, no new research)
  live      Run one short research job and print structured metrics
  watch     Poll latest output json every N seconds while you use the UI

Examples:
  python scripts/inspect_pipeline.py
  python scripts/inspect_pipeline.py --mode live --query "What is CRISPR?"
  python scripts/inspect_pipeline.py --watch --interval 3
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def est_tokens(text: str | Any) -> int:
    if text is None:
        return 0
    if not isinstance(text, str):
        text = str(text)
    return max(1, len(text) // 4)


def latest_file(pattern: str, directory: Path) -> Path | None:
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def extract_metrics_from_log_text(text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "context_size_chars": None,
        "scraped_pages": [],
        "search_hits": [],
        "mcp_results": [],
        "total_costs": [],
    }

    for match in re.finditer(r"Research completed\. Context size: (\d+)", text):
        metrics["context_size_chars"] = int(match.group(1))

    for match in re.finditer(r"Scraped content from (\d+) URLs", text):
        metrics["scraped_pages"].append(int(match.group(1)))

    for match in re.finditer(r"MCP research completed: (\d+) results", text):
        metrics["mcp_results"].append(int(match.group(1)))

    for match in re.finditer(r"Total Research Costs: \$(\d+\.?\d*)", text):
        metrics["total_costs"].append(float(match.group(1)))

    search_patterns = [
        r"searching",
        r"Search results",
        r"Scraping content from (\d+) URLs",
        r"Collected (\d+) sources",
        r"sub.?quer",
    ]
    for line in text.splitlines():
        lower = line.lower()
        if any(re.search(p, lower) for p in search_patterns):
            metrics["search_hits"].append(line.strip()[-200:])

    return metrics


def inspect_output_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    content = data.get("content") or {}
    events = data.get("events") or []

    report = content.get("report") or ""
    context = content.get("context") or []
    sources = content.get("sources") or []
    costs = content.get("costs") or 0.0

    log_outputs: list[str] = []
    for event in events:
        payload = event.get("data") or {}
        output = payload.get("output")
        if output:
            log_outputs.append(str(output))

    combined_logs = "\n".join(log_outputs)
    log_metrics = extract_metrics_from_log_text(combined_logs)

    context_chars = log_metrics["context_size_chars"]
    if context_chars is None and context:
        context_chars = len(str(context))

    return {
        "artifact": str(path),
        "timestamp": data.get("timestamp"),
        "query": content.get("query") or "",
        "report_chars": len(report),
        "report_words": len(report.split()),
        "report_est_tokens": est_tokens(report),
        "context_chars": context_chars,
        "context_est_tokens": est_tokens(str(context)) if context else (est_tokens(context_chars) if context_chars else 0),
        "sources_in_json": len(sources) if isinstance(sources, list) else 0,
        "costs_in_json": costs,
        "event_count": len(events),
        "log_snippets": log_outputs[-8:],
        "log_metrics": log_metrics,
    }


def inspect_app_log(log_path: Path, tail_lines: int = 200) -> dict[str, Any]:
    if not log_path.is_file():
        return {"path": str(log_path), "exists": False}

    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = "\n".join(lines[-tail_lines:])
    metrics = extract_metrics_from_log_text(tail)
    chat_lines = [
        ln for ln in lines[-tail_lines:]
        if any(k in ln for k in ("Performing web search", "Received chat request", "Generated response", "chat"))
    ]
    return {
        "path": str(log_path),
        "exists": True,
        "tail_lines": tail_lines,
        "metrics": metrics,
        "chat_lines": chat_lines[-10:],
    }


def print_summary(payload: dict[str, Any]) -> None:
    print("\n=== Pipeline Trace Summary ===\n")

    if payload.get("output_json"):
        oj = payload["output_json"]
        print(f"Latest run artifact: {oj['artifact']}")
        if oj.get("query"):
            print(f"Query: {oj['query']}")
        print(f"Report: {oj['report_chars']} chars (~{oj['report_est_tokens']} tokens est.)")
        if oj.get("context_chars"):
            print(f"Context fed to writer: {oj['context_chars']} chars (~{oj['context_est_tokens']} tokens est.)")
        print(f"Sources field in json: {oj['sources_in_json']}")
        print(f"WebSocket log events: {oj['event_count']}")
        if oj.get("costs_in_json"):
            print(f"Costs (json): ${oj['costs_in_json']}")

        lm = oj.get("log_metrics") or {}
        if lm.get("scraped_pages"):
            print(f"Scraped URL batches (from logs): {lm['scraped_pages']}")
        if lm.get("mcp_results"):
            print(f"MCP result counts: {lm['mcp_results']}")

        if oj.get("log_snippets"):
            print("\nRecent pipeline logs (UI / websocket):")
            for line in oj["log_snippets"]:
                print(f"  • {line[:160]}")

    if payload.get("app_log"):
        al = payload["app_log"]
        if al.get("exists"):
            print(f"\nBackend log tail: {al['path']}")
            m = al.get("metrics") or {}
            if m.get("context_size_chars"):
                print(f"  Context size (backend): {m['context_size_chars']} chars (~{est_tokens(m['context_size_chars'])} tokens est.)")
            if al.get("chat_lines"):
                print("\nRecent chat/search lines:")
                for line in al["chat_lines"]:
                    print(f"  • {line[-180:]}")

    print("\n--- Chat note ---")
    print("Chat sends: system prompt + full report + message history to the LLM.")
    print("Watch backend for: 'Performing web search for:' (Tavily tool call)")
    print("Chat response metadata may include tool_calls / search_metadata.\n")


async def run_live_trace(query: str, report_source: str = "web") -> dict[str, Any]:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    from gpt_researcher import GPTResearcher
    from gpt_researcher.utils.enum import ReportType, Tone

    started = time.time()
    researcher = GPTResearcher(
        query=query,
        report_type=ReportType.ResearchReport.value,
        report_source=report_source,
        tone=Tone.Objective,
        verbose=True,
    )

    await researcher.conduct_research()
    report = await researcher.write_report()
    elapsed = time.time() - started

    context = researcher.get_research_context()
    context_str = str(context)
    sources = researcher.get_source_urls()
    research_sources = researcher.get_research_sources()

    return {
        "query": query,
        "report_source": report_source,
        "elapsed_sec": round(elapsed, 1),
        "source_url_count": len(sources),
        "research_source_objects": len(research_sources),
        "source_urls_sample": sources[:10],
        "context_chars": len(context_str),
        "context_est_tokens": est_tokens(context_str),
        "report_chars": len(report),
        "report_est_tokens": est_tokens(report),
        "cost_usd": researcher.get_costs(),
        "step_costs": researcher.get_step_costs(),
        "report_preview": report[:400],
    }


def print_live(result: dict[str, Any], save_dir: Path | None) -> None:
    print("\n=== Live Pipeline Trace ===\n")
    print(f"Query: {result['query']}")
    print(f"Elapsed: {result['elapsed_sec']}s")
    print(f"Source URLs: {result['source_url_count']}")
    print(f"Research source objects: {result['research_source_objects']}")
    print(f"Context → model (research): {result['context_chars']} chars (~{result['context_est_tokens']} tokens est.)")
    print(f"Report output: {result['report_chars']} chars (~{result['report_est_tokens']} tokens est.)")
    print(f"Cost (tracked): ${result['cost_usd']:.4f}")
    if result.get("step_costs"):
        print("Step costs:", result["step_costs"])
    if result.get("source_urls_sample"):
        print("\nSample sources:")
        for url in result["source_urls_sample"]:
            print(f"  - {url}")

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "live_trace.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (save_dir / "report_preview.md").write_text(
            result.get("report_preview", ""),
            encoding="utf-8",
        )
        print(f"\nSaved: {save_dir}")


def build_summary() -> dict[str, Any]:
    outputs_dir = ROOT / "outputs"
    log_path = ROOT / "logs" / "app.log"

    payload: dict[str, Any] = {}
    latest = latest_file("task_*.json", outputs_dir) if outputs_dir.is_dir() else None
    if latest:
        payload["output_json"] = inspect_output_json(latest)
    else:
        payload["output_json"] = None

    payload["app_log"] = inspect_app_log(log_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect GPT Researcher pipeline metrics")
    parser.add_argument("--mode", choices=["summary", "live", "watch"], default="summary")
    parser.add_argument("--query", default="What is CRISPR and one application?")
    parser.add_argument("--report-source", default="web", choices=["web", "local", "hybrid"])
    parser.add_argument("--watch", action="store_true", help="Alias for --mode watch")
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--save-dir", default="")
    args = parser.parse_args()

    if args.watch:
        args.mode = "watch"

    os.chdir(ROOT)

    if args.mode == "live":
        result = asyncio.run(run_live_trace(args.query, args.report_source))
        save_dir = Path(args.save_dir) if args.save_dir else ROOT / "outputs" / "trace" / datetime.now().strftime("%Y%m%d_%H%M%S")
        print_live(result, save_dir)
        return 0

    if args.mode == "watch":
        print("Watching latest outputs/task_*.json (Ctrl+C to stop)...")
        last_mtime = 0.0
        try:
            while True:
                outputs_dir = ROOT / "outputs"
                latest = latest_file("task_*.json", outputs_dir) if outputs_dir.is_dir() else None
                if latest and latest.stat().st_mtime > last_mtime:
                    last_mtime = latest.stat().st_mtime
                    payload = {"output_json": inspect_output_json(latest), "app_log": inspect_app_log(ROOT / "logs" / "app.log")}
                    os.system("cls" if os.name == "nt" else "clear")
                    print_summary(payload)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    payload = build_summary()
    if not payload.get("output_json"):
        print("No outputs/task_*.json found yet. Run a research in the UI first,")
        print("or use: python scripts/inspect_pipeline.py --mode live")
        print_summary(payload)
        return 1

    print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
