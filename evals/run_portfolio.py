"""
Portfolio eval pack — produce resume/interview-ready metrics. :-)

Runs:
  1) cheap gates (offline)
  2) full: harness live sample + live chat (if API up)
  3) nightly sample: SimpleQA + hallucination (token cost)

Usage:
  D:\\anaconda3\\envs\\gptresearcher\\python.exe evals/run_portfolio.py --num-examples 3
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "evals" / "results"


def _run(cmd: list[str], env: dict | None = None) -> dict:
    print(f"\n>> {' '.join(cmd)}")
    t0 = time.time()
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=merged, text=True)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "elapsed_sec": round(time.time() - t0, 2),
    }


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_portfolio_md(metrics: dict, path: Path) -> None:
    sqa = metrics.get("simpleqa") or {}
    hall = metrics.get("hallucination") or {}
    live = metrics.get("live_chat") or {}
    cheap = metrics.get("cheap") or {}
    harness = metrics.get("harness_full") or {}
    product = metrics.get("product_strata") or {}

    lines = [
        "# Portfolio evaluation metrics",
        "",
        f"- Generated (UTC): `{metrics.get('timestamp')}`",
        f"- Sample size (SimpleQA requested / hallucination requested): "
        f"**{metrics.get('num_examples')}**",
        f"- Sample seed: **{metrics.get('sample_seed')}**",
        f"- SimpleQA sample mode: **{sqa.get('sample_mode') or metrics.get('sample_mode') or 'n/a'}**",
        "",
        "## Pillar ledger (do not merge into one accuracy)",
        "",
        "| Pillar | What it measures | Notes |",
        "|--------|------------------|-------|",
        "| A Fact (SimpleQA) | short-form factuality | topic-stratified sample |",
        "| B Faithfulness (hallucination) | MAJOR vs evidence pack | full corpus when n≥70 |",
        "| C Product behavior | dialogue / tool / fuzz / memory | cheap JSONL gates |",
        "",
        "## Gate layers",
        "",
        f"| Layer | Result | Notes |",
        f"|-------|--------|-------|",
        f"| cheap (offline) | {'PASS' if cheap.get('ok') else 'FAIL'} | dialogue/tool/memory + report scorers |",
        f"| full harness | {'PASS' if harness.get('ok') else 'FAIL/SKIP'} | live research sample |",
        f"| live chat | {'PASS' if live.get('ok') else 'FAIL/SKIP'} | `/api/chat` tool routing |",
        f"| SimpleQA | see metrics | factuality of research reports |",
        f"| Hallucination | see metrics | faithfulness vs retrieved context |",
        "",
        "## Headline numbers (resume-friendly)",
        "",
        "### A — Fact (SimpleQA)",
        "",
    ]
    sqm = sqa.get("metrics") or {}
    if sqm:
        lines += [
            f"- **accuracy (among attempted):** {sqm.get('accuracy', 0):.1%}",
            f"- **F1:** {sqm.get('f1', 0):.3f}",
            f"- **correct rate:** {sqm.get('correct_rate', 0):.1%} "
            f"({sqm.get('successful', 0)} graded)",
            f"- **effective_n / mode:** {sqa.get('effective_n', sqa.get('num_examples'))} / "
            f"`{sqa.get('sample_mode') or 'n/a'}`",
            f"- **topic strata:** `{sqa.get('strata_counts') or {}}`",
            f"- **answer_type mix (report-only):** `{sqa.get('answer_type_counts') or {}}`",
            f"- **cost:** ${sqm.get('total_cost', 0):.4f}",
            "",
        ]
    else:
        lines += ["- SimpleQA: not available in this run", ""]

    lines += ["### B — Faithfulness (hallucination)", ""]
    if hall:
        rate = hall.get("hallucination_rate")
        rate_s = f"{rate:.1%}" if isinstance(rate, (int, float)) else "n/a"
        sev = hall.get("severity_counts") or {}
        lines += [
            f"- **MAJOR hallucination detection rate:** {rate_s} "
            f"({hall.get('total_hallucinated', 0)}/{hall.get('total_evaluated', 0)} evaluated)",
            f"- **effective_n:** {hall.get('effective_n', hall.get('total_queries'))} "
            f"(requested {hall.get('requested_n', metrics.get('num_examples'))})",
            f"- **Judge mode:** `{hall.get('judge_mode') or hall.get('judge') or 'lite'}`",
        ]
        if sev:
            lines.append(
                f"- **Severity mix:** MAJOR {sev.get('MAJOR', 0)} / "
                f"MINOR {sev.get('MINOR', 0)} / NONE {sev.get('NONE', 0)}"
            )
        by_bucket = hall.get("by_bucket") or {}
        if by_bucket:
            lines.append(f"- **by risk bucket:** `{by_bucket}`")
        lines += [
            f"- **cost:** ${float(hall.get('total_cost') or 0):.4f}",
            "",
        ]
    else:
        lines += ["- Hallucination: not available in this run", ""]

    lines += ["### C — Product behavior", ""]
    if product:
        for pillar, row in product.items():
            lines.append(
                f"- **{pillar}:** active {row.get('active', 0)} "
                f"(blocked {row.get('blocked', 0)})"
            )
        lines.append("")
    else:
        lines += ["- Product strata: not available in this run", ""]

    if live:
        lines += [
            f"- **Live chat cases passed:** {live.get('passed', 0)}/{live.get('total', 0)}",
            "",
        ]

    lines += [
        "## How to explain in interviews",
        "",
        "1. **Cheap gate** catches regressions without spending tokens (intent clarify, tool policy, citations).",
        "2. **Full gate** samples live Agent A (research job) + Agent B (chat tools).",
        "3. **Nightly / portfolio** measures quality with a **pillar ledger**: "
        "SimpleQA topic-stratified factuality + hallucination MAJOR rate (full 70) + product JSONL.",
        "4. Never merge pillars into one “overall accuracy”.",
        "5. Metrics are written to `evals/results/*_latest.json` for audit/repro.",
        "",
        "See [PORTFOLIO.md](../PORTFOLIO.md) for the full narrative.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _product_strata() -> dict:
    """Count active/blocked cases per product pillar JSONL. :-)"""
    if str(REPO_ROOT / "evals") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "evals"))
    from _common import load_jsonl

    out: dict = {}
    for pillar in ("dialogue", "tool", "fuzz", "memory"):
        path = REPO_ROOT / "evals" / f"{pillar}_eval" / "cases.jsonl"
        if not path.is_file():
            continue
        active = load_jsonl(path, suite="cheap", include_blocked=False)
        all_rows = load_jsonl(path, suite="cheap", include_blocked=True)
        blocked = [c for c in all_rows if (c.get("status") or "").lower() == "blocked"]
        out[pillar] = {"active": len(active), "blocked": len(blocked)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio eval pack")
    parser.add_argument("--num-examples", type=int, default=3)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Sample seed for SimpleQA/hallucination (default: EVAL_SAMPLE_SEED or 42)",
    )
    parser.add_argument(
        "--sample-mode",
        choices=["stratified", "random"],
        default="stratified",
        help="SimpleQA sampling mode (default: stratified by topic)",
    )
    parser.add_argument("--harness-limit", type=int, default=1)
    parser.add_argument("--skip-live-chat", action="store_true")
    parser.add_argument("--skip-nightly", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    if sys.version_info < (3, 10):
        print("Need Python >= 3.10", file=sys.stderr)
        raise SystemExit(2)

    # Late import keeps portfolio runnable even if evals helpers change. :-)
    if str(REPO_ROOT / "evals") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "evals"))
    from _common import resolve_sample_seed

    sample_seed = resolve_sample_seed(args.seed)
    py = sys.executable
    RESULTS.mkdir(parents=True, exist_ok=True)
    eval_env = {
        "EVAL_TOTAL_WORDS": os.getenv("EVAL_TOTAL_WORDS") or "350",
        "EVAL_LIVE_CHAT": "1",
        "EVAL_SAMPLE_SEED": str(sample_seed),
        "EVAL_SAMPLE_MODE": args.sample_mode,
    }

    steps = []
    steps.append(_run([py, "evals/run_gates.py", "--suite", "cheap"]))

    steps.append(
        _run(
            [
                py,
                "evals/harness_eval/run_eval.py",
                "--suite",
                "full",
                "--limit",
                str(args.harness_limit),
            ],
            env=eval_env,
        )
    )

    if not args.skip_live_chat:
        steps.append(
            _run(
                [
                    py,
                    "evals/dialogue_eval/run_live.py",
                    "--base-url",
                    args.base_url,
                    "--limit",
                    "3",
                ],
                env=eval_env,
            )
        )

    if not args.skip_nightly:
        steps.append(
            _run(
                [
                    py,
                    "evals/simple_evals/run_eval.py",
                    "--num_examples",
                    str(args.num_examples),
                    "--seed",
                    str(sample_seed),
                    "--sample-mode",
                    args.sample_mode,
                ],
                env=eval_env,
            )
        )
        steps.append(
            _run(
                [
                    py,
                    "evals/hallucination_eval/run_eval.py",
                    "-n",
                    str(args.num_examples),
                    "--judge",
                    "lite",
                    "--seed",
                    str(sample_seed),
                ],
                env=eval_env,
            )
        )

    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "num_examples": args.num_examples,
        "sample_seed": sample_seed,
        "sample_mode": args.sample_mode,
        "product_strata": _product_strata(),
        "cheap": {"ok": steps[0]["ok"], **steps[0]},
        "harness_full": {"ok": steps[1]["ok"], **steps[1]},
        "live_chat": _load_json(RESULTS / "live_chat_latest.json"),
        "simpleqa": _load_json(RESULTS / "simpleqa_latest.json"),
        "hallucination": _load_json(RESULTS / "hallucination_latest.json"),
        "steps": steps,
    }
    # If live chat step failed hard (API down), mark soft in metrics
    if not args.skip_live_chat and len(steps) >= 3 and not steps[2]["ok"]:
        metrics["live_chat"] = {
            **(metrics.get("live_chat") or {}),
            "ok": False,
            "note": "live chat step failed (is API running on --base-url?)",
        }

    out_json = RESULTS / "portfolio_latest.json"
    out_md = RESULTS / "PORTFOLIO_METRICS.md"
    out_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    write_portfolio_md(metrics, out_md)
    print(f"\nWrote {out_json}")
    print(f"Wrote {out_md}")

    # Portfolio run succeeds if cheap passed; nightly failures still recorded for honesty
    if not steps[0]["ok"]:
        raise SystemExit(1)
    print("PORTFOLIO PACK COMPLETE (cheap required; see metrics for nightly quality)")


if __name__ == "__main__":
    main()
