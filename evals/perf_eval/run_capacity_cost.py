"""Controlled capacity + cost benchmarks (NOT production QPS / online AOV). :-)

Phases:
  1) Chat soak — fixed wall time, continuous /api/chat, report req/s + P95 + errors
  2) Short Job batch — concurrency 2, N homogeneous short tasks, cost + completion rate
  3) Medium Job batch — optional comparison cohort

Writes:
  evals/results/capacity_cost_<ts>.json
  evals/results/capacity_cost_latest.json
  evals/results/CAPACITY_COST.md
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PERF_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT / "evals") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "evals"))
if str(PERF_DIR) not in sys.path:
    sys.path.insert(0, str(PERF_DIR))

from p95 import p95, percentile  # noqa: E402

RESULTS = REPO_ROOT / "evals" / "results"
DEFAULT_BASE = os.getenv("EVAL_BASE_URL") or "http://127.0.0.1:8000"

CHAT_PROMPT = "用一句话介绍 GPT Researcher 是什么"
SHORT_TASK = "用80字介绍 Redis 核心用途"
MEDIUM_TASK = "用600字概述向量数据库的主要选型维度与常见产品"


def _http_json(
    url: str,
    *,
    data: dict | None = None,
    headers: dict | None = None,
    timeout: int = 180,
) -> tuple[int, dict, float, str]:
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="GET" if data is None else "POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            set_cookie = resp.headers.get("Set-Cookie") or ""
            return resp.status, payload, (time.perf_counter() - t0) * 1000.0, set_cookie
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": raw[:400]}
        return exc.code, payload, (time.perf_counter() - t0) * 1000.0, ""
    except Exception as exc:  # noqa: BLE001
        return 599, {"error": str(exc)}, (time.perf_counter() - t0) * 1000.0, ""


def _cookie_from_set_cookie(set_cookie: str) -> str:
    text = set_cookie or ""
    for part in text.replace(",", ";").split(";"):
        nv = part.strip()
        if nv.lower().startswith("gptr_uid="):
            return nv
    for part in text.split(";"):
        nv = part.strip()
        if "=" in nv and not nv.lower().startswith(
            ("path=", "max-age=", "expires=", "httponly", "samesite=", "secure")
        ):
            return nv
    return ""


def _bootstrap_cookie(base: str) -> str:
    code, _, _, set_cookie = _http_json(f"{base.rstrip('/')}/api/auth/me", timeout=20)
    if code >= 400:
        return ""
    return _cookie_from_set_cookie(set_cookie)


def _job_status(payload: dict) -> str:
    job = payload.get("job") if isinstance(payload.get("job"), dict) else None
    if job:
        return str(job.get("status") or "")
    return str(payload.get("status") or "")


def _job_blob(payload: dict) -> dict:
    job = payload.get("job") if isinstance(payload.get("job"), dict) else None
    return job or payload


def _probe_env(base: str) -> dict[str, Any]:
    live_code, live, _, _ = _http_json(f"{base.rstrip('/')}/health/live", timeout=10)
    ready_code, ready, _, _ = _http_json(f"{base.rstrip('/')}/health/ready", timeout=15)
    return {
        "base_url": base,
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "live_http": live_code,
        "live": live,
        "ready_http": ready_code,
        "ready": ready,
    }


def run_chat_soak(
    base: str,
    *,
    duration_sec: int,
    concurrency: int,
    prompt: str,
) -> dict[str, Any]:
    """Closed-loop chat soak: workers keep issuing requests until wall clock ends."""
    stop_at = time.time() + max(1, duration_sec)
    latencies_ms: list[float] = []
    errors = 0
    status_counts: dict[str, int] = {}
    lock = threading.Lock()
    started = time.perf_counter()

    def worker() -> None:
        nonlocal errors
        cookie = _bootstrap_cookie(base)
        headers = {"Cookie": cookie} if cookie else {}
        while time.time() < stop_at:
            code, payload, ms, _ = _http_json(
                f"{base.rstrip('/')}/api/chat",
                data={
                    "report": "",
                    "messages": [{"role": "user", "content": prompt}],
                    "research_topic": "",
                    "research_context": "",
                    "report_language": "chinese",
                },
                headers=headers,
                timeout=120,
            )
            key = str(code)
            with lock:
                status_counts[key] = status_counts.get(key, 0) + 1
                if code < 400 and not (
                    isinstance(payload, dict) and payload.get("error") and not payload.get("response")
                ):
                    # Treat HTTP OK as success; chat shapes vary. :-)
                    latencies_ms.append(ms)
                else:
                    errors += 1

    print(
        f"[chat] soak start duration={duration_sec}s concurrency={concurrency} prompt={prompt!r}"
    )
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futs = [pool.submit(worker) for _ in range(max(1, concurrency))]
        for fut in as_completed(futs):
            fut.result()
    elapsed = time.perf_counter() - started
    ok = len(latencies_ms)
    total = ok + errors
    rps = ok / elapsed if elapsed > 0 else 0.0
    err_rate = (errors / total) if total else 1.0
    summary = {
        "phase": "chat_soak",
        "prompt": prompt,
        "duration_sec_target": duration_sec,
        "duration_sec_actual": round(elapsed, 2),
        "concurrency": concurrency,
        "success": ok,
        "errors": errors,
        "total_attempts": total,
        "req_per_sec_success": round(rps, 3),
        "error_rate": round(err_rate, 4),
        "latency_ms": {
            "p50": round(percentile(latencies_ms, 50), 2) if latencies_ms else None,
            "p95": round(p95(latencies_ms), 2) if latencies_ms else None,
            "p99": round(percentile(latencies_ms, 99), 2) if latencies_ms else None,
            "mean": round(statistics.fmean(latencies_ms), 2) if latencies_ms else None,
            "max": round(max(latencies_ms), 2) if latencies_ms else None,
        },
        "http_status_counts": status_counts,
        "caveat": (
            "Closed-loop soak throughput on a single host; "
            "NOT production QPS capacity. Do not derive QPS from concurrency alone."
        ),
    }
    print(
        f"[chat] done success_rps={summary['req_per_sec_success']} "
        f"p95_ms={summary['latency_ms']['p95']} error_rate={summary['error_rate']}"
    )
    return summary


def _create_job(
    base: str,
    *,
    cookie: str,
    task: str,
    total_words: int,
) -> tuple[str, dict]:
    headers = {"Cookie": cookie} if cookie else {}
    last_payload: dict = {}
    for _ in range(10):
        code, payload, _, _ = _http_json(
            f"{base.rstrip('/')}/api/jobs/research",
            data={
                "task": task,
                "report_type": "research_report",
                "report_source": "web",
                "tone": "Objective",
                "report_language": "chinese",
                "total_words": total_words,
                "max_search_results": 2,
            },
            headers=headers,
            timeout=60,
        )
        last_payload = payload if isinstance(payload, dict) else {"raw": payload}
        if code == 429:
            wait = float(last_payload.get("retry_after") or 15)
            time.sleep(min(max(wait, 5.0), 45.0))
            continue
        if code >= 400 or not last_payload.get("job_id"):
            raise RuntimeError(f"create job HTTP {code}: {last_payload}")
        return str(last_payload["job_id"]), last_payload
    raise RuntimeError(f"create job exhausted retries: {last_payload}")


def _wait_job(
    base: str,
    *,
    cookie: str,
    job_id: str,
    timeout_sec: float,
) -> dict[str, Any]:
    headers = {"Cookie": cookie} if cookie else {}
    deadline = time.time() + timeout_sec
    last: dict = {}
    while time.time() < deadline:
        code, payload, _, _ = _http_json(
            f"{base.rstrip('/')}/api/jobs/{job_id}",
            headers=headers,
            timeout=30,
        )
        last = payload if isinstance(payload, dict) else {}
        if code < 400:
            status = _job_status(last)
            if status in {"completed", "failed", "cancelled"}:
                blob = _job_blob(last)
                result = blob.get("result") if isinstance(blob.get("result"), dict) else {}
                cost = result.get("cost") if isinstance(result.get("cost"), dict) else {}
                return {
                    "job_id": job_id,
                    "status": status,
                    "http": code,
                    "cost": cost,
                    "stage": blob.get("stage"),
                    "error": blob.get("error") or result.get("error"),
                }
        time.sleep(1.5)
    blob = _job_blob(last)
    return {
        "job_id": job_id,
        "status": "timeout",
        "http": None,
        "cost": {},
        "stage": blob.get("stage"),
        "error": f"not terminal within {timeout_sec}s",
    }


def run_job_batch(
    base: str,
    *,
    label: str,
    task: str,
    total_words: int,
    n: int,
    concurrency: int,
    timeout_sec: float,
) -> dict[str, Any]:
    job_concurrency = max(1, min(int(concurrency), 2))
    print(
        f"[job:{label}] start n={n} concurrency={job_concurrency} "
        f"total_words={total_words} task={task!r}"
    )
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    walls: list[float] = []
    lock = threading.Lock()

    def one(idx: int) -> dict[str, Any]:
        cookie = _bootstrap_cookie(base)
        t0 = time.perf_counter()
        try:
            job_id, _ = _create_job(
                base, cookie=cookie, task=task, total_words=total_words
            )
            outcome = _wait_job(
                base, cookie=cookie, job_id=job_id, timeout_sec=timeout_sec
            )
            wall = time.perf_counter() - t0
            outcome["wall_sec"] = round(wall, 2)
            outcome["index"] = idx
            return outcome
        except Exception as exc:  # noqa: BLE001
            return {
                "index": idx,
                "job_id": None,
                "status": "error",
                "wall_sec": round(time.perf_counter() - t0, 2),
                "cost": {},
                "error": str(exc)[:300],
            }

    with ThreadPoolExecutor(max_workers=job_concurrency) as pool:
        futs = [pool.submit(one, i) for i in range(n)]
        for fut in as_completed(futs):
            rec = fut.result()
            with lock:
                records.append(rec)
                if rec.get("status") == "completed":
                    walls.append(float(rec.get("wall_sec") or 0.0))
            print(
                f"[job:{label}] #{rec.get('index')} status={rec.get('status')} "
                f"wall={rec.get('wall_sec')}s cost={rec.get('cost')}"
            )

    elapsed = time.perf_counter() - started
    completed = [r for r in records if r.get("status") == "completed"]
    failed = [r for r in records if r.get("status") != "completed"]
    searches = [int((r.get("cost") or {}).get("searches") or 0) for r in completed]
    llm_calls = [int((r.get("cost") or {}).get("llm_calls") or 0) for r in completed]

    def _avg(xs: list[float | int]) -> float | None:
        return round(float(statistics.fmean(xs)), 2) if xs else None

    summary = {
        "phase": f"job_{label}",
        "label": label,
        "task": task,
        "total_words": total_words,
        "n": n,
        "concurrency": job_concurrency,
        "duration_sec_actual": round(elapsed, 2),
        "completed": len(completed),
        "failed_or_other": len(failed),
        "success_rate": round(len(completed) / n, 4) if n else 0.0,
        "jobs_per_hour": round(len(completed) / elapsed * 3600.0, 2) if elapsed > 0 else 0.0,
        "jobs_per_min": round(len(completed) / elapsed * 60.0, 3) if elapsed > 0 else 0.0,
        "wall_sec": {
            "p50": round(percentile(walls, 50), 2) if walls else None,
            "p95": round(p95(walls), 2) if walls else None,
            "mean": _avg(walls),
            "max": round(max(walls), 2) if walls else None,
        },
        "cost_completed_only": {
            "searches_mean": _avg(searches),
            "searches_p50": round(percentile(searches, 50), 2) if searches else None,
            "llm_calls_mean": _avg(llm_calls),
            "llm_calls_p50": round(percentile(llm_calls, 50), 2) if llm_calls else None,
            "note": (
                "Counts from Job.result.cost when present; "
                "USD not inferred. Not an online average order value."
            ),
        },
        "records": sorted(records, key=lambda r: int(r.get("index") or 0)),
        "caveat": (
            "Queue throughput under RESEARCH_MAX_CONCURRENT_GLOBAL≈2 style caps; "
            "report as jobs/hour, not QPS."
        ),
    }
    print(
        f"[job:{label}] done completed={summary['completed']}/{n} "
        f"jobs_per_hour={summary['jobs_per_hour']} "
        f"wall_p95={summary['wall_sec']['p95']} "
        f"llm_mean={summary['cost_completed_only']['llm_calls_mean']}"
    )
    return summary


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    env = report.get("environment") or {}
    ready = env.get("ready") or {}
    checks = ready.get("checks") if isinstance(ready, dict) else {}
    chat = report.get("chat_soak") or {}
    short = report.get("job_short") or {}
    medium = report.get("job_medium") or {}
    lat = chat.get("latency_ms") or {}
    args = report.get("args") or {}

    lines = [
        "# Capacity & cost controlled benchmarks",
        "",
        f"- Generated (UTC): `{report.get('generated_at_utc')}`",
        f"- Base URL: `{env.get('base_url')}`",
        f"- Host: `{env.get('host')}` / Python `{env.get('python')}`",
        f"- Ready: `{ready.get('status') if isinstance(ready, dict) else ready}`",
        "",
        "## Scope / 口径限制（必读）",
        "",
        "1. 本报告是**单机受控实验**，不是生产容量规划，也不是线上真实流量。",
        "2. **禁止**把并发数或 P95 延迟换算成 QPS；Chat 吞吐以实测 `req/s` 为准。",
        "3. Job 侧报告 **jobs/min / jobs/hour**，不要叫 QPS；受全局并发槽位（实验并发≤2）约束。",
        "4. 成本只汇总 `Job.result.cost` 中的 **searches / llm_calls**（完成任务）；",
        "   **没有**稳定线上平均客单价（USD），也不编造 token 均价。",
        "5. 单次任务成本与模型、检索次数、上下文和输出长度强相关；短/中档仅作对比，不可外推。",
        "",
        "## Environment",
        "",
        _md_table(
            ["Check", "OK", "Detail"],
            [
                [
                    k,
                    (v or {}).get("ok") if isinstance(v, dict) else "",
                    (v or {}).get("status") if isinstance(v, dict) else v,
                ]
                for k, v in (checks or {}).items()
            ]
            or [["(none)", "", "ready payload lacked checks"]],
        ),
        "",
        "## Commands",
        "",
        "```bash",
        "D:\\anaconda3\\envs\\gptresearcher\\python.exe evals/perf_eval/run_capacity_cost.py \\",
        f"  --base-url {env.get('base_url') or DEFAULT_BASE} \\",
        f"  --chat-duration-sec {args.get('chat_duration_sec')} \\",
        f"  --chat-concurrency {args.get('chat_concurrency')} \\",
        f"  --short-n {args.get('short_n')} \\",
        f"  --medium-n {args.get('medium_n')} \\",
        f"  --job-concurrency {args.get('job_concurrency')}",
        "```",
        "",
        "Artifacts: `evals/results/capacity_cost_latest.json`, this markdown.",
        "",
        "## 1) Chat soak (throughput)",
        "",
        f"- Prompt: `{chat.get('prompt')}`",
        f"- Target duration: **{chat.get('duration_sec_target')}s** "
        f"(actual **{chat.get('duration_sec_actual')}s**)",
        f"- Concurrency (closed-loop workers): **{chat.get('concurrency')}**",
        "",
        _md_table(
            ["Metric", "Value"],
            [
                ["Success requests", chat.get("success")],
                ["Errors", chat.get("errors")],
                ["Success req/s", chat.get("req_per_sec_success")],
                ["Error rate", chat.get("error_rate")],
                ["Latency p50 (ms)", lat.get("p50")],
                ["Latency p95 (ms)", lat.get("p95")],
                ["Latency p99 (ms)", lat.get("p99")],
                ["Latency mean (ms)", lat.get("mean")],
                ["Latency max (ms)", lat.get("max")],
                ["HTTP status counts", json.dumps(chat.get("http_status_counts") or {}, ensure_ascii=False)],
            ],
        ),
        "",
        f"> {chat.get('caveat')}",
        "",
        "## 2) Short Job batch (cost + throughput)",
        "",
        f"- Task: `{short.get('task')}`",
        f"- `total_words={short.get('total_words')}`, n=**{short.get('n')}**, "
        f"concurrency=**{short.get('concurrency')}**",
        "",
        _md_table(
            ["Metric", "Value"],
            [
                ["Completed / N", f"{short.get('completed')} / {short.get('n')}"],
                ["Success rate", short.get("success_rate")],
                ["Wall clock (batch sec)", short.get("duration_sec_actual")],
                ["Jobs / min", short.get("jobs_per_min")],
                ["Jobs / hour", short.get("jobs_per_hour")],
                ["Wall p50 (sec)", (short.get("wall_sec") or {}).get("p50")],
                ["Wall p95 (sec)", (short.get("wall_sec") or {}).get("p95")],
                ["Wall mean (sec)", (short.get("wall_sec") or {}).get("mean")],
                ["Searches mean (completed)", (short.get("cost_completed_only") or {}).get("searches_mean")],
                ["LLM calls mean (completed)", (short.get("cost_completed_only") or {}).get("llm_calls_mean")],
                ["LLM calls p50 (completed)", (short.get("cost_completed_only") or {}).get("llm_calls_p50")],
            ],
        ),
        "",
        f"> {short.get('caveat')}",
        "",
        "## 3) Medium Job batch (comparison)",
        "",
    ]

    if medium.get("n"):
        lines += [
            f"- Task: `{medium.get('task')}`",
            f"- `total_words={medium.get('total_words')}`, n=**{medium.get('n')}**, "
            f"concurrency=**{medium.get('concurrency')}**",
            "",
            _md_table(
                ["Metric", "Value"],
                [
                    ["Completed / N", f"{medium.get('completed')} / {medium.get('n')}"],
                    ["Success rate", medium.get("success_rate")],
                    ["Wall clock (batch sec)", medium.get("duration_sec_actual")],
                    ["Jobs / min", medium.get("jobs_per_min")],
                    ["Jobs / hour", medium.get("jobs_per_hour")],
                    ["Wall p50 (sec)", (medium.get("wall_sec") or {}).get("p50")],
                    ["Wall p95 (sec)", (medium.get("wall_sec") or {}).get("p95")],
                    ["Wall mean (sec)", (medium.get("wall_sec") or {}).get("mean")],
                    [
                        "Searches mean (completed)",
                        (medium.get("cost_completed_only") or {}).get("searches_mean"),
                    ],
                    [
                        "LLM calls mean (completed)",
                        (medium.get("cost_completed_only") or {}).get("llm_calls_mean"),
                    ],
                    [
                        "LLM calls p50 (completed)",
                        (medium.get("cost_completed_only") or {}).get("llm_calls_p50"),
                    ],
                ],
            ),
            "",
        ]
    else:
        lines += ["_(skipped)_", ""]

    # Comparison table
    lines += [
        "## Short vs medium (side-by-side)",
        "",
        _md_table(
            ["Cohort", "n", "Completed", "Jobs/hour", "Wall p95 (s)", "LLM calls mean", "Searches mean"],
            [
                [
                    "short",
                    short.get("n"),
                    short.get("completed"),
                    short.get("jobs_per_hour"),
                    (short.get("wall_sec") or {}).get("p95"),
                    (short.get("cost_completed_only") or {}).get("llm_calls_mean"),
                    (short.get("cost_completed_only") or {}).get("searches_mean"),
                ],
                [
                    "medium",
                    medium.get("n") or 0,
                    medium.get("completed"),
                    medium.get("jobs_per_hour"),
                    (medium.get("wall_sec") or {}).get("p95") if medium else None,
                    (medium.get("cost_completed_only") or {}).get("llm_calls_mean")
                    if medium
                    else None,
                    (medium.get("cost_completed_only") or {}).get("searches_mean")
                    if medium
                    else None,
                ],
            ],
        ),
        "",
        "## Interview / resume wording (safe)",
        "",
        "- ✅ 「单机受控压测：Chat 可持续约 "
        f"**{chat.get('req_per_sec_success')} req/s**"
        f"（并发 worker={chat.get('concurrency')}，"
        f"P95≈{lat.get('p95')}ms，错误率≈{chat.get('error_rate')}）」",
        "- ✅ 「短 Job（全局并发≤2）完成速率约 "
        f"**{short.get('jobs_per_hour')} jobs/hour**"
        f"，完成任务 LLM 调用均值≈{(short.get('cost_completed_only') or {}).get('llm_calls_mean')}」",
        "- ❌ 不要写「生产 QPS / 线上平均成本」",
        "",
        f"Raw JSON: `{report.get('json_path')}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capacity + cost controlled benchmarks")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--chat-duration-sec", type=int, default=1800, help="default 30min")
    parser.add_argument("--chat-concurrency", type=int, default=5)
    parser.add_argument("--chat-prompt", default=CHAT_PROMPT)
    parser.add_argument("--short-n", type=int, default=15)
    parser.add_argument("--short-words", type=int, default=80)
    parser.add_argument("--short-task", default=SHORT_TASK)
    parser.add_argument("--medium-n", type=int, default=8)
    parser.add_argument("--medium-words", type=int, default=600)
    parser.add_argument("--medium-task", default=MEDIUM_TASK)
    parser.add_argument("--job-concurrency", type=int, default=2)
    parser.add_argument("--job-timeout-sec", type=float, default=900.0)
    parser.add_argument("--skip-chat", action="store_true")
    parser.add_argument("--skip-short", action="store_true")
    parser.add_argument("--skip-medium", action="store_true")
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")
    env = _probe_env(base)
    if int(env.get("live_http") or 599) >= 400:
        raise SystemExit(f"API not live at {base}: {env}")

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": env,
        "args": {
            "chat_duration_sec": args.chat_duration_sec,
            "chat_concurrency": args.chat_concurrency,
            "short_n": args.short_n,
            "medium_n": args.medium_n,
            "job_concurrency": args.job_concurrency,
        },
    }

    if not args.skip_chat:
        report["chat_soak"] = run_chat_soak(
            base,
            duration_sec=args.chat_duration_sec,
            concurrency=args.chat_concurrency,
            prompt=args.chat_prompt,
        )
    else:
        report["chat_soak"] = {"phase": "chat_soak", "skipped": True}

    if not args.skip_short:
        report["job_short"] = run_job_batch(
            base,
            label="short",
            task=args.short_task,
            total_words=args.short_words,
            n=args.short_n,
            concurrency=args.job_concurrency,
            timeout_sec=args.job_timeout_sec,
        )
    else:
        report["job_short"] = {"phase": "job_short", "skipped": True, "n": 0}

    if not args.skip_medium and args.medium_n > 0:
        report["job_medium"] = run_job_batch(
            base,
            label="medium",
            task=args.medium_task,
            total_words=args.medium_words,
            n=args.medium_n,
            concurrency=args.job_concurrency,
            timeout_sec=max(args.job_timeout_sec, 1200.0),
        )
    else:
        report["job_medium"] = {"phase": "job_medium", "skipped": True, "n": 0}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = RESULTS / f"capacity_cost_{ts}.json"
    latest = RESULTS / "capacity_cost_latest.json"
    md_path = RESULTS / "CAPACITY_COST.md"
    report["json_path"] = str(json_path)

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, report)
    print(f"Wrote {json_path}")
    print(f"Wrote {latest}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
