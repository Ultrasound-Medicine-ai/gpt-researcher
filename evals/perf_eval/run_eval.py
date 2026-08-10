"""Perf eval: P95 latency gates for chat (and optional research jobs). :-)

cheap  — schema + offline p95 helper checks (no API)
full   — concurrent live /api/chat; soft-skip if API down unless --strict
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PERF_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT / "evals") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "evals"))
if str(PERF_DIR) not in sys.path:
    sys.path.insert(0, str(PERF_DIR))

from _common import load_jsonl, print_summary, summarize  # noqa: E402
from p95 import p95  # noqa: E402

RESULTS = REPO_ROOT / "evals" / "results"
DEFAULT_BASE = "http://127.0.0.1:8000"


def _http_json(
    url: str,
    *,
    data: dict | None = None,
    headers: dict | None = None,
    timeout: int = 180,
) -> tuple[int, dict, float]:
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
            return resp.status, payload, (time.perf_counter() - t0) * 1000.0
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": raw[:300]}
        return exc.code, payload, (time.perf_counter() - t0) * 1000.0
    except Exception as exc:  # noqa: BLE001
        return 599, {"error": str(exc)}, (time.perf_counter() - t0) * 1000.0


def _api_up(base: str) -> bool:
    code, _, _ = _http_json(f"{base.rstrip('/')}/api/auth/me", timeout=10)
    return code < 500


def _bootstrap_cookie(base: str) -> str:
    code, _, ms = _http_json(f"{base.rstrip('/')}/api/auth/me", timeout=20)
    # urllib doesn't give Set-Cookie easily here; visitor cookie often optional. :-)
    _ = (code, ms)
    return ""


def _chat_once(base: str, user: str, cookie: str) -> float:
    headers = {"Cookie": cookie} if cookie else {}
    code, _, ms = _http_json(
        f"{base.rstrip('/')}/api/chat",
        data={
            "report": "",
            "messages": [{"role": "user", "content": user}],
            "research_topic": "",
            "research_context": "",
            "report_language": "chinese",
        },
        headers=headers,
        timeout=120,
    )
    if code >= 400:
        raise RuntimeError(f"chat HTTP {code}")
    return ms


def _run_chat_p95(case: dict, base: str, *, concurrency: int, requests_n: int) -> dict:
    cookie = _bootstrap_cookie(base)
    user = str(case.get("user") or "你好，简单介绍一下你自己")
    latencies: list[float] = []
    errors = 0

    def _one(_: int) -> float:
        return _chat_once(base, user, cookie)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futs = [pool.submit(_one, i) for i in range(requests_n)]
        for fut in as_completed(futs):
            try:
                latencies.append(fut.result())
            except Exception:  # noqa: BLE001
                errors += 1

    expect = case.get("expect") or {}
    max_ms = float(expect.get("p95_latency_ms_max") or 8000)
    value = p95(latencies) if latencies else float("inf")
    failures: list[str] = []
    if not latencies:
        failures.append("no successful chat samples")
    elif value > max_ms:
        failures.append(f"p95={value:.1f}ms exceeds max={max_ms}ms")
    if errors:
        failures.append(f"{errors}/{requests_n} requests failed")

    return {
        "id": case["id"],
        "passed": len(failures) == 0,
        "failures": failures,
        "p95_ms": round(value, 2) if latencies else None,
        "samples": len(latencies),
        "errors": errors,
        "max_ms": max_ms,
        "concurrency": concurrency,
    }


def _run_job_p95(case: dict, base: str, *, concurrency: int) -> dict:
    """Submit short research jobs and measure wall-clock to terminal status. :-)"""
    expect = case.get("expect") or {}
    max_sec = float(expect.get("p95_wall_sec_max") or 180)
    task = str(case.get("task") or "用100字介绍 Redis 是什么")
    walls: list[float] = []
    errors = 0

    def _one(_: int) -> float:
        t0 = time.perf_counter()
        code, payload, _ = _http_json(
            f"{base.rstrip('/')}/api/jobs/research",
            data={
                "task": task,
                "report_type": "research_report",
                "report_source": "web",
                "tone": "Objective",
                "report_language": "chinese",
            },
            timeout=60,
        )
        if code >= 400 or not payload.get("job_id"):
            raise RuntimeError(f"create job failed HTTP {code}: {payload}")
        job_id = payload["job_id"]
        deadline = time.time() + max_sec + 30
        while time.time() < deadline:
            c2, st, _ = _http_json(
                f"{base.rstrip('/')}/api/jobs/{job_id}", timeout=30
            )
            status = str((st or {}).get("status") or "")
            if c2 < 400 and status in {"completed", "failed", "cancelled"}:
                return time.perf_counter() - t0
            time.sleep(1.5)
        raise TimeoutError(f"job {job_id} not terminal within budget")

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futs = [pool.submit(_one, i) for i in range(concurrency)]
        for fut in as_completed(futs):
            try:
                walls.append(fut.result())
            except Exception:  # noqa: BLE001
                errors += 1

    value = p95(walls) if walls else float("inf")
    failures: list[str] = []
    if not walls:
        failures.append("no successful jobs")
    elif value > max_sec:
        failures.append(f"p95={value:.1f}s exceeds max={max_sec}s")
    if errors:
        failures.append(f"{errors}/{concurrency} jobs failed")

    return {
        "id": case["id"],
        "passed": len(failures) == 0,
        "failures": failures,
        "p95_sec": round(value, 2) if walls else None,
        "samples": len(walls),
        "errors": errors,
        "max_sec": max_sec,
        "concurrency": concurrency,
    }


def run_cheap() -> dict:
    cases_path = Path(__file__).parent / "cases.jsonl"
    cases = load_jsonl(cases_path, suite="full", include_blocked=True)
    # Schema gate: every case needs id + expect threshold. :-)
    results = []
    for case in cases:
        expect = case.get("expect") or {}
        failures = []
        if not case.get("id"):
            failures.append("missing id")
        if case.get("target") == "chat" and "p95_latency_ms_max" not in expect:
            failures.append("chat case missing p95_latency_ms_max")
        if case.get("target") == "job" and "p95_wall_sec_max" not in expect:
            failures.append("job case missing p95_wall_sec_max")
        # Offline math smoke
        if abs(p95([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) - 10.0) > 1e-6:
            failures.append("p95 helper regression")
        results.append(
            {
                "id": case.get("id") or "unknown",
                "passed": len(failures) == 0,
                "failures": failures,
                "skipped": False,
                "mode": "schema",
            }
        )
    summary = summarize(results, pillar="perf", suite="cheap")
    print_summary(summary)
    _write_latest(summary)
    return summary


def run_full(
    base: str,
    *,
    strict: bool,
    skip_jobs: bool,
    concurrency: int,
    chat_requests: int,
) -> dict:
    cases_path = Path(__file__).parent / "cases.jsonl"
    cases = load_jsonl(cases_path, suite="full", include_blocked=True)
    if not _api_up(base):
        note = f"API not reachable at {base}"
        if strict:
            summary = {
                "pillar": "perf",
                "suite": "full",
                "total": 0,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "ok": False,
                "note": note,
                "results": [{"id": "api", "passed": False, "failures": [note]}],
            }
            print_summary(summary)
            _write_latest(summary)
            return summary
        summary = {
            "pillar": "perf",
            "suite": "full",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": len(cases),
            "ok": True,
            "note": note + " (soft-skip)",
            "results": [
                {"id": c.get("id"), "skipped": True, "reason": note} for c in cases
            ],
        }
        print_summary(summary)
        _write_latest(summary)
        return summary

    results = []
    for case in cases:
        target = case.get("target")
        if target == "job" and skip_jobs:
            results.append(
                {
                    "id": case["id"],
                    "skipped": True,
                    "reason": "job P95 skipped (set --include-jobs to enable)",
                }
            )
            continue
        if target == "chat":
            results.append(
                _run_chat_p95(
                    case,
                    base,
                    concurrency=concurrency,
                    requests_n=chat_requests,
                )
            )
        elif target == "job":
            results.append(
                _run_job_p95(case, base, concurrency=min(concurrency, 3))
            )
        else:
            results.append(
                {
                    "id": case.get("id"),
                    "skipped": True,
                    "reason": f"unknown target={target}",
                }
            )

    summary = summarize(results, pillar="perf", suite="full")
    print_summary(summary)
    _write_latest(summary)
    return summary


def _write_latest(summary: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {
        **summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = RESULTS / "perf_latest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Perf P95 eval")
    parser.add_argument("--suite", default="cheap", choices=["cheap", "full"])
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--strict", action="store_true", help="Fail if API down")
    parser.add_argument(
        "--include-jobs",
        action="store_true",
        help="Also run research-job P95 (expensive)",
    )
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--chat-requests", type=int, default=10)
    args = parser.parse_args()

    if args.suite == "cheap":
        summary = run_cheap()
    else:
        summary = run_full(
            args.base_url,
            strict=args.strict,
            skip_jobs=not args.include_jobs,
            concurrency=args.concurrency,
            chat_requests=args.chat_requests,
        )
    raise SystemExit(0 if summary.get("ok") else 1)


if __name__ == "__main__":
    main()
