"""Build Project-2 metrics dashboard + regression queue from local artifacts. :-)

Inputs (best-effort):
  evals/results/gate_*_latest.json
  evals/results/portfolio_latest.json
  evals/results/simpleqa_latest.json
  evals/results/hallucination_latest.json
  evals/results/dialogue_latest.json
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
    for source in ("dialogue", "live_chat"):
        routing = artifacts.get(source) or {}
        for row in routing.get("results") or []:
            if row.get("predicted_intent"):
                spans.append(
                    {
                        "trace_type": "intent_route",
                        "source": source,
                        "id": row.get("id"),
                        "expected": row.get("expected_intent"),
                        "predicted": row.get("predicted_intent"),
                        "report_created": row.get("report_created"),
                        "duration_sec": row.get("elapsed_sec"),
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


def _intent_metric_lines(name: str, metrics: dict[str, Any]) -> list[str]:
    if not metrics:
        return [f"### {name}", "", "_No labelled routing artifact._", ""]
    lines = [
        f"### {name}",
        "",
        f"- Accuracy: **{metrics.get('accuracy', 'n/a')}**; "
        f"macro P/R/F1: **{metrics.get('macro_precision', 'n/a')} / "
        f"{metrics.get('macro_recall', 'n/a')} / {metrics.get('macro_f1', 'n/a')}**",
        f"- Route false-positive rate: "
        f"**{metrics.get('report_route_false_positive_rate', 'n/a')}** "
        f"({metrics.get('report_route_false_positives', 0)}/"
        f"{metrics.get('non_create_requests', 0)})",
        f"- Actual false-creation rate: "
        f"**{metrics.get('false_report_creation_rate', 'n/a')}** "
        f"({metrics.get('false_report_creations', 0)}/"
        f"{metrics.get('non_create_requests_with_side_effect_observation', 0)})",
        f"- Guarded route false positives: "
        f"**{metrics.get('guarded_report_route_false_positives', 0)}**",
        "",
        "| Intent | Precision | Recall | F1 | Support |",
        "|--------|-----------|--------|----|---------|",
    ]
    for intent, values in (metrics.get("per_class") or {}).items():
        lines.append(
            f"| `{intent}` | {values.get('precision')} | {values.get('recall')} | "
            f"{values.get('f1')} | {values.get('support')} |"
        )
    lines += [
        "",
        f"Confusion matrix (expected → predicted): "
        f"`{metrics.get('confusion_matrix') or {}}`",
        "",
    ]
    return lines


def render_md(artifacts: dict[str, Any], failures: list[dict], traces: dict) -> str:
    cheap = artifacts.get("gate_cheap") or {}
    portfolio = artifacts.get("portfolio") or {}
    sqa = artifacts.get("simpleqa") or {}
    hall = artifacts.get("hallucination") or {}
    live = artifacts.get("live_chat") or {}
    dialogue = artifacts.get("dialogue") or {}
    perf = artifacts.get("perf") or {}
    extended = {name: artifacts.get(name) or {} for name in ("intent", "multiturn", "tool_chain", "fuzz", "memory", "security", "trace_replay")}
    sqm = sqa.get("metrics") or {}
    live_intent_metrics = live.get("intent_metrics") or {}
    cheap_intent_metrics = dialogue.get("intent_metrics") or {}

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
        "## Intent routing",
        "",
        *_intent_metric_lines("Cheap deterministic routing", cheap_intent_metrics),
        *_intent_metric_lines("Live LLM routing", live_intent_metrics),
        "## Offline Agent evaluation harness (seed=42)",
        "",
        "| Pillar | N | Pass / fail | Key ratios | Blocked | Latest run |",
        "|--------|---|-------------|------------|---------|------------|",
    ]
    for name, payload in extended.items():
        if name == "trace_replay":
            total = payload.get("replay_case_count", 0)
            passed = payload.get("reproducible_failure_count", 0)
            key = f"spans={payload.get('span_count', 0)}; reproducible_failures={passed}"
        else:
            total = payload.get("total", 0)
            passed = payload.get("passed", 0)
            key = ", ".join(f"{k}={v}" for k, v in list((payload.get("metrics") or {}).items())[:3]) or "n/a"
        lines.append(f"| {name} | {total} | {passed} / {payload.get('failed', 0)} | {key} | 0 | {payload.get('timestamp', 'local offline')} |")
    lines += ["", "## Perf P95", ""]
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

    lines += ["", "## Latest controlled evaluations", ""]
    for name in ("live_intent_expanded", "live_intent_holdout", "judge_stability", "judge_calibration", "retrieval", "planning", "planning_holdout"):
        payload = artifacts.get(name) or {}
        metric_blob = payload.get("intent_metrics") or payload.get("metrics") or {
            key: payload.get(key) for key in ("severity_exact_agreement", "major_non_major_agreement", "subgoal_coverage", "coverage", "constraint_retention", "redundant_step_rate", "duplicate_subtask_rate", "irrelevant_step_rate", "irrelevant_subtask_rate", "executable_plan_rate") if key in payload
        }
        lines.append(f"- `{name}`: status={payload.get('status', 'n/a')}; N={payload.get('total', 0)}; `{metric_blob}`; {payload.get('reason', '')}")

    lines += [
        "",
        "## Interpretation limits",
        "",
        "- Live Intent results are controlled test cases, **not production accuracy**. The frozen pre-fix result remains in its JSON artifact for regression history but is not a current headline.",
        "- Judge historical replay is **BLOCKED** because the original 70-case artifact retained only an 800-character evidence preview. New hallucination evaluations now persist `evidence_pack`; no historical evidence was fabricated or regenerated.",
        "- Retrieval is document-level testing of the existing keyword fallback only; it does **not** represent PGVector semantic-retrieval quality.",
        "- Planning metrics use the normalized scorer (`normalized_keyword_v2`) and existing Planner outputs; no Planner model was rerun during scorer correction.",
    ]
    lines += ["", "## Planning by scenario", ""]
    for name in ("planning", "planning_holdout"):
        payload=artifacts.get(name) or {}
        lines.append(f"### {name} (N={payload.get('total', 0)})")
        lines.append("")
        lines.append("| Scenario | N | Subgoal coverage | Constraint retention | Redundant | Irrelevant | Executable |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for scenario, metric in (payload.get("category_metrics") or {}).items():
            lines.append(f"| {scenario} | {metric.get('n', 0)} | {metric.get('subgoal_coverage', 0):.2%} | {metric.get('constraint_retention', 0):.2%} | {metric.get('redundant_step_rate', 0):.2%} | {metric.get('irrelevant_step_rate', 0):.2%} | {metric.get('executable_plan_rate', 0):.2%} |")
        scenario_failures=payload.get("failure_case_ids") or [item.get("case_id") for item in payload.get("failed_cases") or []]
        lines.append(f"- failure case IDs: {', '.join(scenario_failures) if scenario_failures else 'none'}")
        lines.append("")

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
        "dialogue": _load(RESULTS / "dialogue_latest.json"),
        "perf": _load(RESULTS / "perf_latest.json"),
        "intent": _load(RESULTS / "intent_latest.json"),
        "multiturn": _load(RESULTS / "multiturn_latest.json"),
        "tool_chain": _load(RESULTS / "tool_chain_latest.json"),
        "fuzz": _load(RESULTS / "fuzz_latest.json"),
        "memory": _load(RESULTS / "memory_latest.json"),
        "security": _load(RESULTS / "security_latest.json"),
        "trace_replay": _load(RESULTS / "trace_replay_latest.json"),
        "live_intent_expanded": _load(RESULTS / "live_intent_expanded.json"),
        "live_intent_before_fix": _load(RESULTS / "live_intent_expanded_before_fix.json"),
        "live_intent_holdout": _load(RESULTS / "live_intent_holdout.json"),
        "judge_stability": _load(RESULTS / "judge_stability_latest.json"),
        "judge_calibration": _load(RESULTS / "judge_calibration_latest.json"),
        "retrieval": _load(RESULTS / "retrieval_latest.json"),
        "planning": _load(RESULTS / "planning_latest.json"),
        "planning_holdout": _load(RESULTS / "planning_holdout_latest.json"),
    }
    failures = collect_failures(artifacts)
    traces = build_trace_index(artifacts)
    replay = artifacts.get("trace_replay") or {}
    if replay.get("spans"):
        traces.update({key: replay[key] for key in ("replay_case_count", "reproducible_failure_count", "failure_stage_distribution")})
        traces["spans"] = replay["spans"][:200]
        traces["span_count"] = len(traces["spans"])
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
