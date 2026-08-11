"""Build Project-2 metrics dashboard + regression queue from local artifacts. :-)

Inputs (best-effort):
  evals/results/gate_*_latest.json
  evals/results/portfolio_latest.json
  evals/results/simpleqa_latest.json
  evals/results/hallucination_latest.json
  evals/results/live_chat_latest.json
  evals/results/perf_latest.json
  evals/fuzz_eval/weaknesses.jsonl

Outputs:
  evals/results/DASHBOARD.md
  evals/results/dashboard.html
  evals/results/regression_queue.jsonl
  evals/results/trace_index.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = REPO_ROOT / "evals" / "results"
FUZZ_WEAK = REPO_ROOT / "evals" / "fuzz_eval" / "weaknesses.jsonl"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def collect_failures(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for name, payload in artifacts.items():
        if not payload:
            continue
        # Gate step failures
        for step in payload.get("steps") or []:
            if step.get("ok") is False:
                failures.append(
                    {
                        "source": name,
                        "kind": "gate_step",
                        "cmd": " ".join(str(x) for x in (step.get("cmd") or [])),
                        "returncode": step.get("returncode"),
                    }
                )
        # Suite result rows
        for row in payload.get("results") or []:
            if row.get("passed") is False and not row.get("skipped"):
                failures.append(
                    {
                        "source": name,
                        "kind": "case",
                        "id": row.get("id") or row.get("query") or row.get("input"),
                        "failures": row.get("failures") or [],
                        "severity": row.get("severity"),
                        "reasoning": (row.get("reasoning") or "")[:240],
                    }
                )
        # Hallucination MAJOR rows
        if name == "hallucination":
            for row in payload.get("results") or []:
                if row.get("is_hallucination") is True:
                    failures.append(
                        {
                            "source": name,
                            "kind": "hallucination_major",
                            "id": row.get("input"),
                            "severity": row.get("severity"),
                            "reasoning": (row.get("reasoning") or "")[:240],
                        }
                    )
        # SimpleQA incorrect
        if name == "simpleqa":
            for row in payload.get("results") or []:
                if row.get("evaluation_grade") == "INCORRECT":
                    failures.append(
                        {
                            "source": name,
                            "kind": "simpleqa_incorrect",
                            "id": row.get("query"),
                            "gold": row.get("gold_answer"),
                        }
                    )
    # Fuzz weaknesses already recorded
    for w in _load_jsonl(FUZZ_WEAK):
        failures.append(
            {
                "source": "fuzz_weaknesses",
                "kind": "fuzz",
                "id": w.get("id"),
                "user": w.get("user"),
                "failures": w.get("failures") or [],
                "status": w.get("status") or "open",
            }
        )
    return failures


def build_trace_index(artifacts: dict[str, Any]) -> dict[str, Any]:
    """Lightweight trace index for interview/repro (not full APM). :-)"""
    spans = []
    # Perf latencies as pseudo-spans
    perf = artifacts.get("perf") or {}
    for row in perf.get("results") or []:
        if row.get("p95_ms") is not None:
            spans.append(
                {
                    "trace_type": "perf_chat_p95",
                    "id": row.get("id"),
                    "duration_ms": row.get("p95_ms"),
                    "ok": row.get("passed"),
                }
            )
        if row.get("p95_sec") is not None:
            spans.append(
                {
                    "trace_type": "perf_job_p95",
                    "id": row.get("id"),
                    "duration_sec": row.get("p95_sec"),
                    "ok": row.get("passed"),
                }
            )
    # Gate step timings
    for suite in ("cheap", "full", "nightly"):
        gate = artifacts.get(f"gate_{suite}") or {}
        for step in gate.get("steps") or []:
            cmd = step.get("cmd") or []
            spans.append(
                {
                    "trace_type": "gate_step",
                    "suite": suite,
                    "cmd": " ".join(str(x) for x in cmd[-3:]),
                    "duration_sec": step.get("elapsed_sec"),
                    "ok": step.get("ok"),
                }
            )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "span_count": len(spans),
        "spans": spans[:200],
    }


def render_md(artifacts: dict[str, Any], failures: list[dict], traces: dict) -> str:
    cheap = artifacts.get("gate_cheap") or {}
    portfolio = artifacts.get("portfolio") or {}
    sqa = artifacts.get("simpleqa") or {}
    hall = artifacts.get("hallucination") or {}
    live = artifacts.get("live_chat") or {}
    perf = artifacts.get("perf") or {}
    sqm = sqa.get("metrics") or {}

    lines = [
        "# Project-2 evaluation dashboard",
        "",
        f"- Generated (UTC): `{datetime.now(timezone.utc).isoformat()}`",
        f"- Regression queue size: **{len(failures)}**",
        f"- Trace spans indexed: **{traces.get('span_count', 0)}**",
        "",
        "## Gate layers",
        "",
        f"| Layer | OK | Notes |",
        f"|-------|----|-------|",
        f"| cheap | {cheap.get('ok')} | offline dialogue/tool/memory/fuzz/perf-schema |",
        f"| portfolio | {bool(portfolio)} | resume pack present={'yes' if portfolio else 'no'} |",
        f"| live chat | {live.get('ok')} | {live.get('passed', 0)}/{live.get('total', 0)} |",
        f"| perf | {perf.get('ok')} | {perf.get('note') or perf.get('suite') or ''} |",
        "",
        "## Quality headlines",
        "",
        f"- SimpleQA accuracy: **{sqm.get('accuracy', 'n/a')}** "
        f"(seed={sqa.get('sample_seed')}, mode={sqa.get('sample_mode')})",
        f"- SimpleQA F1: **{sqm.get('f1', 'n/a')}**",
        f"- SimpleQA topic strata: `{sqa.get('strata_counts') or {}}`",
        f"- Hallucination rate: **{hall.get('hallucination_rate', 'n/a')}** "
        f"(judge={hall.get('judge_mode') or hall.get('judge')}, "
        f"effective_n={hall.get('effective_n', hall.get('total_queries'))})",
        f"- Hallucination severity: `{hall.get('severity_counts')}`",
        f"- Hallucination by_bucket: `{hall.get('by_bucket') or {}}`",
        "",
        "## Perf P95",
        "",
    ]
    for row in perf.get("results") or []:
        if row.get("skipped"):
            lines.append(f"- SKIP `{row.get('id')}`: {row.get('reason')}")
        elif row.get("p95_ms") is not None:
            mark = "PASS" if row.get("passed") else "FAIL"
            lines.append(
                f"- {mark} `{row.get('id')}` p95={row.get('p95_ms')}ms "
                f"(max {row.get('max_ms')}ms, n={row.get('samples')})"
            )
        elif row.get("p95_sec") is not None:
            mark = "PASS" if row.get("passed") else "FAIL"
            lines.append(
                f"- {mark} `{row.get('id')}` p95={row.get('p95_sec')}s "
                f"(max {row.get('max_sec')}s, n={row.get('samples')})"
            )
        else:
            mark = "PASS" if row.get("passed") else "FAIL"
            lines.append(f"- {mark} `{row.get('id')}` mode={row.get('mode')}")

    lines += ["", "## Regression queue (top 20)", ""]
    if not failures:
        lines.append("_Empty — no open failures harvested._")
    for item in failures[:20]:
        lines.append(
            f"- `{item.get('kind')}` / `{item.get('id')}` "
            f"← {item.get('source')} {item.get('failures') or ''}"
        )

    lines += [
        "",
        "## Closed loop",
        "",
        "1. Run gates / portfolio / fuzz → artifacts under `evals/results/`.",
        "2. `python evals/dashboard/build_dashboard.py` rebuilds this page + queue.",
        "3. Fuzz failures append `evals/fuzz_eval/weaknesses.jsonl`; "
        "promote with `python evals/fuzz_eval/promote_weaknesses.py`.",
        "4. Trace index: `evals/results/trace_index.json` (gate/perf spans).",
        "",
    ]
    return "\n".join(lines)


def render_html(md_text: str) -> str:
    # Minimal static HTML; keep dependency-free. :-)
    escaped = (
        md_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>Project-2 Dashboard</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; line-height: 1.5; }}
    pre {{ white-space: pre-wrap; background: #f6f8fa; padding: 1rem; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>Project-2 evaluation dashboard</h1>
  <p>Generated from local eval artifacts. Source markdown mirrored below.</p>
  <pre>{escaped}</pre>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Project-2 dashboard")
    parser.add_argument(
        "--out-dir",
        default=str(RESULTS),
        help="Output directory (default evals/results)",
    )
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "gate_cheap": _load(RESULTS / "gate_cheap_latest.json"),
        "gate_full": _load(RESULTS / "gate_full_latest.json"),
        "gate_nightly": _load(RESULTS / "gate_nightly_latest.json"),
        "portfolio": _load(RESULTS / "portfolio_latest.json"),
        "simpleqa": _load(RESULTS / "simpleqa_latest.json"),
        "hallucination": _load(RESULTS / "hallucination_latest.json"),
        "live_chat": _load(RESULTS / "live_chat_latest.json"),
        "perf": _load(RESULTS / "perf_latest.json"),
    }
    failures = collect_failures(artifacts)
    traces = build_trace_index(artifacts)
    md = render_md(artifacts, failures, traces)

    (out_dir / "DASHBOARD.md").write_text(md, encoding="utf-8")
    (out_dir / "dashboard.html").write_text(render_html(md), encoding="utf-8")
    (out_dir / "trace_index.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    queue_path = out_dir / "regression_queue.jsonl"
    with open(queue_path, "w", encoding="utf-8") as f:
        for item in failures:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Wrote {out_dir / 'DASHBOARD.md'}")
    print(f"Wrote {out_dir / 'dashboard.html'}")
    print(f"Wrote {out_dir / 'trace_index.json'}")
    print(f"Wrote {queue_path} ({len(failures)} items)")


if __name__ == "__main__":
    main()
