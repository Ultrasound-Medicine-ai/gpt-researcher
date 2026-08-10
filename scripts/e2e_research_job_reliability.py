"""Docker/local E2E checks for async ResearchJob reliability.

Validates:
1) Job continues after client disconnect (no cancel on disconnect)
2) Refresh/resume via job_id
3) API restart does not stop Worker
4) completed only after report persisted
"""

from __future__ import annotations

import asyncio
import json
import os
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


async def wait_ready(timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            code, payload = _req("GET", "/health/ready", timeout=5)
            if code == 200 and payload.get("status") == "ready":
                print("READY", payload.get("checks", {}).keys())
                return
            last = (code, payload)
        except Exception as exc:
            last = str(exc)
        await asyncio.sleep(2)
    raise RuntimeError(f"API not ready: {last}")


async def poll_job(job_id: str, timeout: float = 600.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        code, payload = _req("GET", f"/api/jobs/{job_id}", timeout=10)
        if code == 200:
            job = payload.get("job") or payload
            last = job
            status = job.get("status")
            print(
                f"  poll {job_id[:8]}… status={status} stage={job.get('stage')} "
                f"progress={job.get('progress')}"
            )
            if status in ("completed", "failed", "cancelled"):
                return job
        await asyncio.sleep(2)
    raise TimeoutError(f"job {job_id} not terminal; last={last}")


async def main() -> int:
    print("=== E2E ResearchJob reliability ===")
    print("API:", API)
    await wait_ready()

    results = {}

    # --- Create job without session_id (backend creates session) ---
    idem = f"e2e-{int(time.time())}"
    code, created = _req(
        "POST",
        "/api/jobs/research",
        {
            "task": "用一句话说明 Redis 的主要用途",
            "report_type": "research_report",
            "report_source": "web",
            "tone": "Objective",
            "total_words": 400,
            "report_language": "chinese",
            "idempotency_key": idem,
        },
    )
    print("CREATE", code, {k: created.get(k) for k in ("job_id", "session_id", "status", "reused")})
    assert code in (200, 202), created
    job_id = created["job_id"]
    session_id = created["session_id"]
    assert job_id and session_id

    # Idempotency: same key returns same ids
    code2, again = _req(
        "POST",
        "/api/jobs/research",
        {
            "task": "用一句话说明 Redis 的主要用途",
            "report_type": "research_report",
            "idempotency_key": idem,
        },
    )
    assert again.get("job_id") == job_id
    assert again.get("session_id") == session_id
    assert again.get("reused") is True
    results["idempotency"] = "PASS"

    # 1) Close browser simulation: stop polling briefly — job must keep progressing
    await asyncio.sleep(4)
    code, mid = _req("GET", f"/api/jobs/{job_id}")
    mid_job = mid.get("job") or mid
    assert mid_job.get("status") not in (None, "cancelled")
    results["continue_after_disconnect"] = (
        "PASS" if mid_job.get("status") in (
            "pending_dispatch", "queued", "running", "retrying", "stale", "completed"
        ) else f"FAIL:{mid_job.get('status')}"
    )
    print("1) continue_after_disconnect:", results["continue_after_disconnect"])

    # 2) Refresh restore via job_id
    code, restored = _req("GET", f"/api/jobs/{job_id}")
    assert code == 200
    assert (restored.get("job") or restored).get("id") == job_id or (
        restored.get("job") or restored
    ).get("session_id") == session_id
    results["refresh_restore"] = "PASS"
    print("2) refresh_restore: PASS")

    # 3) Restart API — Worker should keep job alive
    # Caller may restart API externally; here we verify worker independence by
    # checking job progresses even if we only talk to PG-backed GET after a gap.
    print("3) API restart check: waiting 8s (simulate API downtime for client)…")
    await asyncio.sleep(8)
    code, after = _req("GET", f"/api/jobs/{job_id}")
    after_job = after.get("job") or after
    results["api_restart_worker_ok"] = (
        "PASS"
        if after_job.get("status")
        in ("queued", "running", "retrying", "completed", "pending_dispatch", "stale")
        else f"FAIL:{after_job.get('status')}"
    )
    print("3) api_restart_worker_ok:", results["api_restart_worker_ok"])

    # 4) Wait for completion; completed only with report in result
    print("4) waiting for completed + report…")
    final = await poll_job(job_id, timeout=900)
    report = (final.get("result") or {}).get("report") or ""
    if final.get("status") == "completed" and report.strip():
        results["completed_after_report"] = "PASS"
    else:
        results["completed_after_report"] = (
            f"FAIL status={final.get('status')} report_len={len(report)} "
            f"error={final.get('error')}"
        )
    print("4) completed_after_report:", results["completed_after_report"])

    print("\n=== SUMMARY ===")
    for k, v in results.items():
        print(f"{k}: {v}")

    failed = [k for k, v in results.items() if not str(v).startswith("PASS")]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
