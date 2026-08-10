"""Submit real research topics, wait for jobs, export Shadow A/B review packs. :-)

Phase A usage (recommended for human review of 10–20 topics):

  python scripts/shadow_review_run.py --limit 8 --force-sample

Without --force-sample, only ~GRAY% of jobs enter Shadow (often 0 hits on a short batch).

Requires API + worker up, and for --force-sample:
  TRUSTED_REPORT_ALLOW_FORCE_SAMPLE=true
  TRUSTED_REPORT_PIPELINE_ENABLED=true
  TRUSTED_REPORT_SHADOW_MODE=true
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Unbuffered progress when launched from IDE/agent shells. :-)
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPICS = ROOT / "scripts" / "shadow_review_topics.txt"
OUT_ROOT = ROOT / "outputs" / "shadow_review"


def _http_json(
    method: str,
    url: str,
    payload: Optional[dict] = None,
    *,
    headers: Optional[dict] = None,
    timeout: float = 60.0,
) -> tuple[int, dict]:
    body = None
    req_headers = {"Accept": "application/json", "User-Agent": "shadow-review-run/1.0"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=req_headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw.strip() else {}
            return resp.status, data if isinstance(data, dict) else {"data": data}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            data = {"raw": raw[:800]}
        if not isinstance(data, dict):
            data = {"data": data}
        return exc.code, data


def load_topics(path: Path, limit: int) -> list[str]:
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
        if len(lines) >= limit:
            break
    return lines


def submit_job(
    api: str,
    task: str,
    *,
    force_sample: bool,
    total_words: int,
    report_type: str,
    user_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    payload = {
        "task": task,
        "report_type": report_type,
        "report_source": "web",
        "tone": "Objective",
        "total_words": total_words,
        "report_language": "chinese",
        "force_trusted_sample": force_sample,
        "idempotency_key": f"shadow-review:{uuid.uuid4()}",
    }
    status, data = _http_json(
        "POST",
        f"{api.rstrip('/')}/api/jobs/research",
        payload,
        headers={"X-User-Id": user_id, "X-Tenant-Id": tenant_id},
        timeout=60.0,
    )
    if status == 429:
        detail = data.get("detail") if isinstance(data.get("detail"), dict) else {}
        retry_after = int(data.get("retry_after") or detail.get("retry_after") or 30)
        raise RuntimeError(f"rate_limited retry_after={retry_after} detail={data}")
    if status >= 400 or not data.get("job_id"):
        raise RuntimeError(f"submit_failed status={status} body={data}")
    return data


def get_job(api: str, job_id: str, *, user_id: str, tenant_id: str) -> dict[str, Any]:
    status, data = _http_json(
        "GET",
        f"{api.rstrip('/')}/api/jobs/{job_id}",
        headers={"X-User-Id": user_id, "X-Tenant-Id": tenant_id},
        timeout=30.0,
    )
    if status >= 400:
        raise RuntimeError(f"get_job_failed status={status} body={data}")
    return data.get("job") or data


def wait_job(
    api: str,
    job_id: str,
    *,
    user_id: str,
    tenant_id: str,
    timeout_sec: int,
    poll_sec: float,
) -> dict[str, Any]:
    terminal = {"completed", "failed", "cancelled"}
    deadline = time.time() + timeout_sec
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = get_job(api, job_id, user_id=user_id, tenant_id=tenant_id)
        st = last.get("status")
        stage = last.get("stage")
        progress = (last.get("progress") or "")[:80]
        print(f"  [{job_id[:8]}] status={st} stage={stage} progress={progress}")
        if st in terminal:
            return last
        time.sleep(poll_sec)
    raise TimeoutError(f"job {job_id} not terminal after {timeout_sec}s last={last.get('status')}")


def clip(text: str, n: int = 12000) -> str:
    text = text or ""
    return text if len(text) <= n else text[:n] + "\n\n…[truncated]…"


def write_review_pack(batch_dir: Path, idx: int, task: str, job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result") or {}
    shadow = result.get("trusted_shadow") or {}
    legacy = result.get("report") or ""
    trusted = shadow.get("report") or ""
    compare = shadow.get("compare") or {}
    audit = shadow.get("audit") or {}
    mode = (result.get("trusted_pipeline") or {}).get("mode")
    jid = job.get("id") or "unknown"
    # Count as hit when trusted draft exists (even if citation audit failed). :-)
    hit_shadow = bool(trusted.strip()) if isinstance(trusted, str) else bool(trusted)

    md = f"""# Shadow review #{idx}: `{jid}`

- Question: {task}
- status: `{job.get("status")}`
- report_trust (delivered): `{result.get("report_trust", "")}`
- trusted_pipeline.mode: `{mode}`
- shadow_hit: `{hit_shadow}`
- shadow_error: `{shadow.get("error") or ""}`

## Compare metrics
```json
{json.dumps(compare, ensure_ascii=False, indent=2)}
```

## Audit (trusted)
```json
{json.dumps(audit, ensure_ascii=False, indent=2)}
```

## Checklist (human)
- [ ] 漏证据：关键事实是否有可核验引用？
- [ ] 逻辑性：结构/论证是否连贯，有无明显自相矛盾？
- [ ] 成本/耗时：trusted 相对 legacy 是否可接受？（见 compare）
- [ ] 是否值得进入 Phase B 灰度交付？

## Legacy report (delivered)
{clip(str(legacy))}

## Trusted report (shadow only)
{clip(str(trusted))}
"""
    stem = f"{idx:02d}_{jid}"
    (batch_dir / f"{stem}.md").write_text(md, encoding="utf-8")
    (batch_dir / f"{stem}.json").write_text(
        json.dumps(
            {"task": task, "job": job},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return {
        "n": idx,
        "job_id": jid,
        "task": task,
        "status": job.get("status"),
        "mode": mode,
        "shadow_hit": hit_shadow,
        "md": f"{stem}.md",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=os.environ.get("GPTR_API", "http://localhost:8000"))
    parser.add_argument("--topics-file", type=Path, default=DEFAULT_TOPICS)
    parser.add_argument("--limit", type=int, default=8, help="How many topics to run")
    parser.add_argument("--total-words", type=int, default=800)
    parser.add_argument("--report-type", default="research_report")
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--poll-sec", type=float, default=8.0)
    parser.add_argument(
        "--force-sample",
        action="store_true",
        help="Force each job into Shadow/trusted sample (needs ALLOW_FORCE_SAMPLE)",
    )
    parser.add_argument("--user-id", default="shadow-review")
    parser.add_argument("--tenant-id", default="shadow-review")
    parser.add_argument(
        "--unique-users",
        action="store_true",
        default=True,
        help="Use shadow-review-<n> user ids to avoid per-user concurrency=1 (default on)",
    )
    parser.add_argument("--shared-user", action="store_true", help="Force single user-id")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep going if one job fails/times out",
    )
    args = parser.parse_args()

    if not args.topics_file.is_file():
        print(f"topics file missing: {args.topics_file}")
        return 2

    topics = load_topics(args.topics_file, args.limit)
    if not topics:
        print("no topics loaded")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = OUT_ROOT / stamp
    batch_dir.mkdir(parents=True, exist_ok=True)

    print(f"API={args.api}")
    print(f"topics={len(topics)} force_sample={args.force_sample}")
    print(f"out={batch_dir}")
    if not args.force_sample:
        print(
            "NOTE: without --force-sample, only ~GRAY% jobs enter Shadow; "
            "short batches may get zero dual-writes."
        )

    index: list[dict[str, Any]] = []
    for i, task in enumerate(topics, start=1):
        print(f"\n=== [{i}/{len(topics)}] submit ===\n{task}", flush=True)
        user_id = (
            args.user_id
            if args.shared_user
            else f"{args.user_id}-{i}"
        )
        try:
            # Capacity gates: serialize; back off on 429. :-)
            while True:
                try:
                    created = submit_job(
                        args.api,
                        task,
                        force_sample=args.force_sample,
                        total_words=args.total_words,
                        report_type=args.report_type,
                        user_id=user_id,
                        tenant_id=args.tenant_id,
                    )
                    break
                except RuntimeError as exc:
                    msg = str(exc)
                    if "rate_limited" in msg:
                        wait = 30
                        if "retry_after=" in msg:
                            try:
                                wait = int(msg.split("retry_after=")[1].split()[0])
                            except Exception:
                                wait = 30
                        print(f"  capacity/budget limited, sleep {wait}s…", flush=True)
                        time.sleep(max(5, wait))
                        continue
                    raise

            job_id = created["job_id"]
            print(f"  job_id={job_id} status={created.get('status')}", flush=True)
            job = wait_job(
                args.api,
                job_id,
                user_id=user_id,
                tenant_id=args.tenant_id,
                timeout_sec=args.timeout_sec,
                poll_sec=args.poll_sec,
            )
            meta = write_review_pack(batch_dir, i, task, job)
            index.append(meta)
            print(
                f"  done status={meta['status']} mode={meta['mode']} "
                f"shadow_hit={meta['shadow_hit']}"
            )
        except (TimeoutError, RuntimeError, URLError, OSError) as exc:
            print(f"  ERROR: {exc}")
            index.append(
                {
                    "n": i,
                    "task": task,
                    "error": str(exc)[:500],
                    "shadow_hit": False,
                }
            )
            if not args.continue_on_error:
                break

    summary = {
        "created_at": stamp,
        "api": args.api,
        "force_sample": args.force_sample,
        "count": len(index),
        "shadow_hits": sum(1 for x in index if x.get("shadow_hit")),
        "items": index,
    }
    (batch_dir / "index.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\n=== summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nReview packs → {batch_dir}")
    if summary["shadow_hits"] == 0:
        print(
            "No Shadow hits. Re-run with --force-sample after enabling "
            "TRUSTED_REPORT_ALLOW_FORCE_SAMPLE=true on the worker."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
