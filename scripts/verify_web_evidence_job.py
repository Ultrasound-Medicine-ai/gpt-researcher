"""Submit a short research job and print timing + Evidence Pack signals. :-)"""

from __future__ import annotations

import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TASK = "简述 Server-Sent Events 原理，要求两百字以内"

_cj = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))


def _req(method: str, path: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with _opener.open(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def main() -> int:
    print(f"API={BASE}")
    try:
        me = _req("GET", "/api/auth/me")
        print(
            "auth:",
            {
                "user_id": me.get("user_id"),
                "tenant_id": me.get("tenant_id"),
                "kind": me.get("kind"),
            },
        )
    except Exception as exc:
        print("auth/me failed:", exc)
        return 1

    t0 = time.time()
    try:
        created = _req(
            "POST",
            "/api/jobs/research",
            {
                "task": TASK,
                "report_type": "research_report",
                "report_source": "web",
                "tone": "Objective",
                "total_words": 300,
                "report_language": "chinese",
                "knowledge_policy": "local_first",
            },
        )
    except urllib.error.HTTPError as exc:
        print("create failed:", exc.read().decode("utf-8", errors="replace")[:500])
        return 1

    job_id = created.get("job_id") or created.get("id")
    print("created job:", job_id, "status=", created.get("status"), "session=", created.get("session_id"))
    if not job_id:
        print("FAIL: no job_id", created)
        return 1

    last: dict = {}
    for _ in range(200):
        time.sleep(2)
        try:
            last = _req("GET", f"/api/jobs/{job_id}")
        except urllib.error.HTTPError as exc:
            print("poll error", exc.code)
            continue
        job = last.get("job") if isinstance(last.get("job"), dict) else last
        status = job.get("status")
        stage = job.get("stage")
        progress = job.get("progress")
        elapsed = time.time() - t0
        print(f"[{elapsed:6.1f}s] status={status} stage={stage} progress={progress}")
        if status in {"completed", "failed", "cancelled"}:
            last = job
            break

    elapsed = time.time() - t0
    job = last.get("job") if isinstance(last.get("job"), dict) else last
    result = job.get("result") or {}
    report = (result.get("report") or "")
    ckpt = job.get("checkpoint_json") or job.get("checkpoint") or {}
    if isinstance(ckpt, str):
        try:
            ckpt = json.loads(ckpt)
        except Exception:
            ckpt = {}
    source_policy = ckpt.get("source_policy") if isinstance(ckpt, dict) else None

    print("---")
    print("final_status:", job.get("status"))
    print("elapsed_sec:", round(elapsed, 1))
    print("source_policy:", source_policy)
    print("report_len:", len(report))
    print("report_preview:", report.replace("\n", " ")[:200])
    print("error:", job.get("error"))
    cost = result.get("cost") or {}
    if cost:
        print("cost:", json.dumps(cost, ensure_ascii=False)[:600])

    ok = job.get("status") == "completed"
    if ok:
        print("PASS: job completed")
        if elapsed < 160:
            print("PASS: wall time under prior ~170s baseline")
        else:
            print("NOTE: completed but >=160s — LLM still dominates")
        return 0
    print("FAIL: job did not complete")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
