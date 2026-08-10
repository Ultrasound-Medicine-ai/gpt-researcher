"""E2E: cancel mid-run, kill-worker stale recovery, visible limits/budgets.

Requires API + Worker + Postgres + Redis already running.
Env:
  E2E_API_URL=http://127.0.0.1:8000
  E2E_WORKER_CONTAINER=gpt-researcher-research-worker-1  (optional for kill test)
  RESEARCH_JOB_STALE_SEC=10  (must match the API container for a fast local run)
  RESEARCH_HEARTBEAT_INTERVAL_SEC=2  (set on the Worker; must be lower than stale)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass

API = os.getenv("E2E_API_URL", "http://127.0.0.1:8000").rstrip("/")
WORKER_CONTAINER = os.getenv(
    "E2E_WORKER_CONTAINER", "gpt-researcher-research-worker-1"
)
STALE_SEC = int(os.getenv("RESEARCH_JOB_STALE_SEC", "90"))


def _req(method: str, path: str, body: dict | None = None, timeout: float = 30.0):
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"detail": raw}
        return exc.code, payload


def wait_ready(timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            code, payload = _req("GET", "/health/ready", timeout=5)
            if code == 200 and payload.get("status") == "ready":
                print("READY")
                return
            last = (code, payload)
        except Exception as exc:
            last = str(exc)
        time.sleep(2)
    raise RuntimeError(f"API not ready: {last}")


def create_job(task: str, **extra) -> dict:
    body = {
        "task": task,
        "report_type": "research_report",
        "report_source": "web",
        "tone": "Objective",
        "total_words": extra.pop("total_words", 300),
        "report_language": "chinese",
        "idempotency_key": f"e2e-ctrl-{int(time.time()*1000)}-{extra.pop('tag', 'x')}",
    }
    body.update(extra)
    code, created = _req("POST", "/api/jobs/research", body)
    assert code in (200, 202), created
    assert created.get("job_id"), created
    return created


def get_job(job_id: str) -> dict:
    code, payload = _req("GET", f"/api/jobs/{job_id}")
    assert code == 200, payload
    return payload.get("job") or payload


def poll_until(job_id: str, statuses: set[str], timeout: float = 300.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = get_job(job_id)
        st = last.get("status")
        print(
            f"  {job_id[:8]} status={st} stage={last.get('stage')} "
            f"code={last.get('last_error_code')} progress={last.get('progress')}"
        )
        if st in statuses:
            return last
        time.sleep(2)
    raise TimeoutError(f"job {job_id} not in {statuses}; last={last}")


def poll_until_fresh_attempt(job_id: str, timeout: float = 120.0) -> dict:
    """Wait until a requeued job has been claimed by a new worker attempt."""
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = get_job(job_id)
        status = last.get("status")
        attempt = int(last.get("attempt") or 0)
        print(
            f"  {job_id[:8]} status={status} attempt={attempt} "
            f"stage={last.get('stage')} code={last.get('last_error_code')}"
        )
        if status == "running" and attempt >= 2:
            return last
        if status in {"failed", "completed", "cancelled"}:
            return last
        time.sleep(2)
    raise TimeoutError(f"job {job_id} did not start a fresh attempt; last={last}")


def docker(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cancel() -> str:
    print("\n=== 1) Cancel mid-run ===")
    created = create_job(
        "请深入调研全球云计算市场近五年趋势、竞争格局与技术演进，并分多章节展开",
        tag="cancel",
        total_words=800,
    )
    job_id = created["job_id"]
    # Prefer cancel while running so cooperative abort is exercised; fall back if queued.
    seen = poll_until(
        job_id, {"running", "queued", "completed", "failed", "cancelled"}, timeout=120
    )
    if seen.get("status") == "completed":
        print("WARN job completed before cancel — retrying with longer task wait")
    code, cancel_resp = _req("POST", f"/api/jobs/{job_id}/cancel")
    print("CANCEL", code, cancel_resp, "from", seen.get("status"))
    assert code == 200
    assert cancel_resp.get("status") in ("cancel_requested", "cancelling", "cancelled")
    final = poll_until(
        job_id, {"cancelled", "failed", "completed"}, timeout=240
    )
    assert final.get("status") == "cancelled", final
    assert (final.get("last_error_code") or "cancelled") == "cancelled"
    report = (final.get("result") or {}).get("report") or ""
    assert not report.strip(), "cancelled job must not expose a completed report"
    print("PASS cancel → cancelled; no completed report")
    return "PASS"


def test_stale_recovery() -> str:
    print("\n=== 2) Kill worker → stale → recover ===")
    # Ensure worker container exists
    ps = docker("ps", "--format", "{{.Names}}")
    if WORKER_CONTAINER not in (ps.stdout or ""):
        print(f"SKIP stale test — container {WORKER_CONTAINER} not running")
        print("  names:", (ps.stdout or "").strip())
        return "SKIP"

    created = create_job(
        "请简述 Redis 与 Memcached 的差异，并给出选型建议",
        tag="stale",
        total_words=400,
    )
    job_id = created["job_id"]
    poll_until(job_id, {"running"}, timeout=120)

    print(f"Killing worker container {WORKER_CONTAINER}…")
    stop = docker("stop", "-t", "0", WORKER_CONTAINER)
    assert stop.returncode == 0, stop.stderr

    # Wait for reaper: stale then queued/retrying/failed
    wait = STALE_SEC + 45
    print(f"Waiting up to {wait}s for stale/requeue…")
    mid = poll_until(
        job_id,
        {"stale", "queued", "retrying", "pending_dispatch", "failed", "completed"},
        timeout=wait,
    )
    print("AFTER_STALE", mid.get("status"), mid.get("last_error_code"), mid.get("progress"))
    assert mid.get("last_error_code") in ("stale_worker", "stale_exhausted") or mid.get(
        "status"
    ) in ("stale", "pending_dispatch", "queued", "failed", "completed"), mid

    print("Starting worker again…")
    start = docker("start", WORKER_CONTAINER)
    assert start.returncode == 0, start.stderr

    resumed = poll_until_fresh_attempt(job_id, timeout=max(STALE_SEC + 45, 90))
    assert resumed.get("status") == "running", resumed
    assert int(resumed.get("attempt") or 0) >= 2, resumed

    # Recovery is now proven. Cancel immediately so this health check does not
    # spend cloud-model quota waiting for an entire report to finish.
    code, cancel_resp = _req("POST", f"/api/jobs/{job_id}/cancel")
    assert code == 200, cancel_resp
    final = poll_until(job_id, {"cancelled", "failed", "completed"}, timeout=120)
    assert final.get("status") == "cancelled", final
    print("PASS stale -> re-dispatch -> fresh worker attempt -> cancelled")
    return "PASS"


def test_budget_clamp_visible() -> str:
    print("\n=== 3) Budget / limits visibility ===")
    # Unit-level sanity via API job that completes with clamped words
    from jobs.budget import clamp_output_words, count_words, truncate_to_words

    assert clamp_output_words(300, 500) == 300
    assert clamp_output_words(9000, 3000) == 3000
    huge = "云计算 " * 5000
    trimmed = truncate_to_words(huge, 300)
    assert count_words(trimmed) <= 320  # small slack for marker
    assert "truncated" in trimmed.lower() or count_words(trimmed) <= 300

    # Job GET should expose attempt / last_error_code fields
    created = create_job("一句话解释什么是向量数据库", tag="budget", total_words=200)
    job_id = created["job_id"]
    job = get_job(job_id)
    assert "attempt" in job
    code, cancel_resp = _req("POST", f"/api/jobs/{job_id}/cancel")
    assert code == 200, cancel_resp
    final = poll_until(job_id, {"cancelled", "failed", "completed"}, timeout=120)
    assert final.get("status") == "cancelled", final
    print(
        "limits env:",
        {
            "RESEARCH_JOB_TIMEOUT_SEC": os.getenv("RESEARCH_JOB_TIMEOUT_SEC", "1800"),
            "RESEARCH_JOB_MAX_ATTEMPTS": os.getenv("RESEARCH_JOB_MAX_ATTEMPTS", "3"),
            "RESEARCH_MAX_OUTPUT_WORDS": os.getenv("RESEARCH_MAX_OUTPUT_WORDS", "3000"),
            "RESEARCH_MAX_TOTAL_SEARCHES": os.getenv("RESEARCH_MAX_TOTAL_SEARCHES", "12"),
        },
    )
    print("PASS budget helpers + job fields present")
    return "PASS"


def main() -> int:
    print("=== E2E cancel / stale / budget ===")
    print("API:", API)
    wait_ready()
    results = {
        "cancel": test_cancel(),
        "stale_recovery": test_stale_recovery(),
        "budget_limits": test_budget_clamp_visible(),
    }
    print("\n=== SUMMARY ===")
    for k, v in results.items():
        print(f"{k}: {v}")
    failed = [k for k, v in results.items() if v not in ("PASS", "SKIP")]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
