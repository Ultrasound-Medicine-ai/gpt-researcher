"""Export Shadow dual-write jobs for human A/B review (legacy vs trusted). :-)

Usage:
  python scripts/shadow_review_export.py
  python scripts/shadow_review_export.py --limit 20 --api http://localhost:8000

Writes markdown packs under outputs/shadow_review/ for 10–20 real topics.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "shadow_review"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _list_jobs_from_api(api: str, limit: int) -> list[dict]:
    """Best-effort: try common admin/list endpoints; fall back to empty."""
    candidates = [
        f"{api.rstrip('/')}/api/jobs?limit={limit * 5}",
        f"{api.rstrip('/')}/jobs?limit={limit * 5}",
    ]
    for url in candidates:
        try:
            data = _get(url)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("jobs", "items", "data"):
                    if isinstance(data.get(key), list):
                        return data[key]
        except Exception:
            continue
    return []


def _load_jobs_from_docker_psql(limit: int) -> list[dict]:
    """Pull recent completed jobs with trusted_shadow from Postgres via docker. :-)"""
    import subprocess

    sql = f"""
SELECT id::text, status, result
FROM research_jobs
WHERE status = 'completed'
  AND result ? 'trusted_shadow'
  AND result->'trusted_shadow' IS NOT NULL
  AND coalesce(result->'trusted_shadow'->>'error', '') = ''
ORDER BY finished_at DESC NULLS LAST
LIMIT {int(limit)};
"""
    try:
        proc = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                os.environ.get("POSTGRES_USER", "gptr"),
                "-d",
                os.environ.get("POSTGRES_DB", "gptr"),
                "-t",
                "-A",
                "-F",
                "\t",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(ROOT),
        )
    except Exception as exc:
        print(f"psql via docker failed: {exc}")
        return []

    if proc.returncode != 0:
        # Table/column names may differ; try jobs table. :-)
        sql2 = sql.replace("research_jobs", "jobs")
        proc = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                os.environ.get("POSTGRES_USER", "gptr"),
                "-d",
                os.environ.get("POSTGRES_DB", "gptr"),
                "-t",
                "-A",
                "-F",
                "\t",
                "-c",
                sql2,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            print((proc.stderr or proc.stdout or "")[:800])
            return []

    rows = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        jid, status, result_raw = parts[0], parts[1], parts[2]
        try:
            result = json.loads(result_raw) if result_raw else {}
        except json.JSONDecodeError:
            continue
        rows.append({"id": jid, "status": status, "result": result})
    return rows


def _job_from_http(api: str, job_id: str) -> dict | None:
    for path in (f"/api/jobs/{job_id}", f"/jobs/{job_id}"):
        try:
            return _get(f"{api.rstrip('/')}{path}")
        except Exception:
            continue
    return None


def _pack_markdown(job: dict, idx: int) -> str:
    result = job.get("result") or {}
    if not isinstance(result, dict) and isinstance(job.get("data"), dict):
        result = job["data"].get("result") or job["data"]
    shadow = result.get("trusted_shadow") or {}
    legacy = result.get("report") or ""
    trusted = shadow.get("report") or ""
    compare = shadow.get("compare") or {}
    audit = shadow.get("audit") or {}
    question = (
        (job.get("params") or {}).get("task")
        or (result.get("task") if isinstance(result.get("task"), str) else "")
        or ""
    )
    jid = job.get("id") or job.get("job_id") or f"idx-{idx}"

    def clip(s: str, n: int = 12000) -> str:
        s = s or ""
        return s if len(s) <= n else s[:n] + "\n\n…[truncated]…"

    return f"""# Shadow review #{idx}: `{jid}`

- Question: {question or "(see job params)"}
- report_trust (delivered): `{result.get("report_trust", "legacy_unverified")}`
- trusted_pipeline.mode: `{(result.get("trusted_pipeline") or {}).get("mode")}`

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--api", default=os.environ.get("GPTR_API", "http://localhost:8000"))
    parser.add_argument(
        "--job-id",
        action="append",
        default=[],
        help="Explicit job id(s); can repeat. Skips discovery when set.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = OUT_DIR / stamp
    batch_dir.mkdir(parents=True, exist_ok=True)

    jobs: list[dict] = []
    if args.job_id:
        for jid in args.job_id:
            data = _job_from_http(args.api, jid)
            if data:
                jobs.append(data if "result" in data else {"id": jid, **data})
            else:
                print(f"warn: could not fetch job {jid}")
    else:
        jobs = _load_jobs_from_docker_psql(args.limit)
        if not jobs:
            jobs = [
                j
                for j in _list_jobs_from_api(args.api, args.limit)
                if (j.get("result") or {}).get("trusted_shadow")
            ][: args.limit]

    index = []
    for i, job in enumerate(jobs[: args.limit], start=1):
        jid = job.get("id") or job.get("job_id") or f"{i}"
        md = _pack_markdown(job, i)
        path = batch_dir / f"{i:02d}_{jid}.md"
        path.write_text(md, encoding="utf-8")
        raw = batch_dir / f"{i:02d}_{jid}.json"
        raw.write_text(json.dumps(job, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        index.append({"n": i, "job_id": jid, "md": str(path.name)})

    summary = {
        "created_at": stamp,
        "count": len(index),
        "items": index,
        "note": "Phase A: users still receive legacy; compare packs for human review.",
    }
    (batch_dir / "index.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Exported {len(index)} shadow review pack(s) → {batch_dir}")
    if not index:
        print(
            "No shadow jobs found yet. With Phase A flags on, wait for ~5% of "
            "completed tasks, then re-run or pass --job-id."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
