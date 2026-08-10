"""E2E: concurrency slots — global=2 reject 3rd; cancel frees; Redis restart rebuilds.

Requires API + Worker + Postgres + Redis.
Env:
  E2E_API_URL=http://127.0.0.1:8000
  E2E_REDIS_CONTAINER=gpt-researcher-redis-1  (optional, for restart test)
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
REDIS_CONTAINER = os.getenv("E2E_REDIS_CONTAINER", "gpt-researcher-redis-1")


def _req(
    method: str,
    path: str,
    body: dict | None = None,
    *,
    user_id: str = "anonymous",
    timeout: float = 30.0,
):
    data = None
    headers = {
        "Content-Type": "application/json",
        "X-User-Id": user_id,
        "X-Tenant-Id": f"tenant-{user_id}",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            retry = resp.headers.get("Retry-After")
            payload = json.loads(raw) if raw else {}
            if retry:
                payload["_retry_after"] = retry
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"detail": raw}
        retry = exc.headers.get("Retry-After") if exc.headers else None
        if retry:
            payload["_retry_after"] = retry
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


def create_job(task: str, user_id: str, **extra) -> tuple[int, dict]:
    body = {
        "task": task,
        "report_type": "research_report",
        "report_source": "web",
        "tone": "Objective",
        "total_words": 200,
        "report_language": "chinese",
        "idempotency_key": f"e2e-slot:{user_id}:{int(time.time() * 1000)}:{task[:40]}",
        **extra,
    }
    return _req("POST", "/api/jobs/research", body, user_id=user_id)


def cancel_job(job_id: str, user_id: str) -> tuple[int, dict]:
    return _req("POST", f"/api/jobs/{job_id}/cancel", user_id=user_id)


def get_job(job_id: str, user_id: str) -> tuple[int, dict]:
    return _req("GET", f"/api/jobs/{job_id}", user_id=user_id)


def main() -> int:
    wait_ready()
    stamp = int(time.time())
    users = [f"slot-e2e-a-{stamp}", f"slot-e2e-b-{stamp}", f"slot-e2e-c-{stamp}"]
    jobs: list[tuple[str, str]] = []

    # Best-effort: cancel any leftover active jobs via API (anonymous) so PG
    # precheck starts clean. Prefer dedicated users below for the real test.
    print("\n=== 0) Preflight (expect empty capacity) ===")
    probe_user = f"slot-e2e-probe-{stamp}"
    code, payload = create_job("slot preflight probe", probe_user)
    if code in (200, 202) and payload.get("job_id"):
        cancel_job(payload["job_id"], probe_user)
        time.sleep(0.5)
    elif code == 429:
        print(
            "WARN: capacity already full before test — "
            "cancel leftover jobs or clear PG active rows, then retry"
        )
        return 1

    print("\n=== 1) Fill 2 global slots ===")
    for uid in users[:2]:
        code, payload = create_job(f"slot hold {uid}", uid)
        print(f"  create {uid}: {code} {payload.get('status') or payload.get('error_code')}")
        if code not in (200, 202):
            print("FAIL: expected accept for first two users")
            return 1
        jid = payload.get("job_id")
        if not jid:
            print("FAIL: missing job_id")
            return 1
        jobs.append((uid, jid))

    print("\n=== 2) Third request must be 429 ===")
    code, payload = create_job(f"slot reject {users[2]}", users[2])
    print(f"  create {users[2]}: {code} {payload}")
    if code != 429:
        print("FAIL: expected HTTP 429 when global slots full")
        # cleanup
        for uid, jid in jobs:
            cancel_job(jid, uid)
        return 1
    if not payload.get("_retry_after") and not payload.get("retry_after"):
        print("WARN: missing Retry-After (body or header)")
    if payload.get("error_code") not in (
        "global_concurrency_limit",
        "queue_full",
        "user_concurrency_limit",
    ):
        print(f"WARN: unexpected error_code={payload.get('error_code')}")

    print("\n=== 3) Cancel one → can create immediately ===")
    uid0, jid0 = jobs[0]
    c_code, c_payload = cancel_job(jid0, uid0)
    print(f"  cancel {jid0}: {c_code} {c_payload.get('status')}")
    # Wait briefly for slot release
    time.sleep(1)
    code, payload = create_job(f"slot after cancel {users[2]}", users[2])
    print(f"  create after cancel: {code} {payload.get('status') or payload}")
    if code not in (200, 202):
        print("FAIL: expected accept after cancel frees a slot")
        for uid, jid in jobs[1:]:
            cancel_job(jid, uid)
        return 1
    jobs[0] = (users[2], payload["job_id"])

    print("\n=== 4) Redis restart → slots rebuild from PG ===")
    try:
        subprocess.run(
            ["docker", "restart", REDIS_CONTAINER],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        print(f"  restarted {REDIS_CONTAINER}")
    except Exception as exc:
        print(f"SKIP redis restart: {exc}")
        for uid, jid in jobs:
            cancel_job(jid, uid)
        print("\nPASS (partial — redis restart skipped)")
        return 0

    wait_ready(timeout=120)
    # Trigger rebuild via reaper tick or create attempt that should still be limited
    time.sleep(5)
    fourth = f"slot-e2e-d-{stamp}"
    code, payload = create_job(f"slot after redis restart {fourth}", fourth)
    print(f"  create after redis restart: {code} {payload.get('error_code') or payload.get('status')}")
    # Still 2 active → should reject
    if code != 429:
        print("FAIL: expected 429 after redis restart (slots should rebuild from PG)")
        for uid, jid in jobs:
            cancel_job(jid, uid)
        return 1

    print("\n=== cleanup ===")
    for uid, jid in jobs:
        cancel_job(jid, uid)
        # Running jobs become cancel_requested until worker observes cancel;
        # after Redis bounce wait for terminal or force another cancel.
        deadline = time.time() + 45
        while time.time() < deadline:
            gcode, gpayload = get_job(jid, uid)
            status = (gpayload.get("job") or gpayload).get("status")
            if status in ("cancelled", "failed", "completed"):
                break
            if status in ("cancel_requested", "cancelling", "running", "queued"):
                cancel_job(jid, uid)
            time.sleep(1.5)

    time.sleep(2)
    code, payload = create_job(f"slot free {fourth}", fourth)
    print(f"  create after full cleanup: {code} {payload.get('status') or payload.get('error_code')}")
    if code in (200, 202) and payload.get("job_id"):
        cancel_job(payload["job_id"], fourth)
    else:
        print("WARN: cleanup may not have freed slots yet (non-blocking)")

    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
