"""Watch frontend-created research jobs and record performance acceptance metrics. :-)"""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "perf_acceptance"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH = OUT_DIR / "summary.json"
TARGET_RUNS = 3
FIXED_TASK_HINT = "Redis 分布式锁原理简述"
POLL_SEC = 4
MAX_WAIT_PER_JOB_SEC = 900
# Seed with already-recorded jobs so monitor only waits for remaining runs. :-)
SEED_JOB_IDS = {
    "bbc6a5ba-9126-4ead-bcec-b3892abf17d2",
}
SEED_RECORDED = 1


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _ts(v) -> float | None:
    if v is None:
        return None
    x = float(v)
    return x / 1000.0 if x > 1e12 else x


def _docker_logs_since(service: str, since: str) -> str:
    try:
        proc = subprocess.run(
            ["docker", "compose", "logs", "--no-color", "--since", since, service],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        return (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:
        return f"<<log_error:{exc}>>"


def discover_job_ids_from_next_logs(since: str, known: set[str]) -> list[str]:
    text = _docker_logs_since("gptr-nextjs", since)
    found = []
    # Prefer create path; poll lines may include stale localStorage resume IDs. :-)
    for m in re.finditer(
        r"POST /api/jobs/research",
        text,
        flags=re.IGNORECASE,
    ):
        pass
    for m in re.finditer(
        r"GET /api/jobs/([0-9a-f-]{36})",
        text,
        flags=re.IGNORECASE,
    ):
        jid = m.group(1)
        if jid not in known and jid not in found:
            found.append(jid)
    for m in re.finditer(
        r"research:([0-9a-f-]{36})",
        _docker_logs_since("research-worker", since),
        flags=re.IGNORECASE,
    ):
        jid = m.group(1)
        if jid not in known and jid not in found:
            found.append(jid)
    return found


def is_job_after_cutoff(job_id: str, cutoff_epoch: float) -> bool:
    """Only accept jobs created after the monitor started. :-)"""
    try:
        data = _get(f"http://localhost:3000/api/jobs/{job_id}")
        job = data.get("job") or data
        created = _ts(job.get("created_at"))
        if created is None:
            return False
        # 5s skew allowance for clock/log delay
        return created >= (cutoff_epoch - 5)
    except Exception:
        return False


def analyze_report(report: str) -> dict:
    body = report
    refs = ""
    if "参考文献" in report:
        body, _, refs = report.partition("参考文献")
    elif "## References" in report:
        body, _, refs = report.partition("## References")
    body_cites = sorted({int(x) for x in re.findall(r"\[(\d+)\]", body)})
    ref_ids = [int(x) for x in re.findall(r'id="ref-(\d+)"', report)]
    headings = re.findall(r"^#{1,3}\s+.+$", report, flags=re.M)
    return {
        "report_chars": len(report),
        "report_cjk_chars": len(re.findall(r"[\u4e00-\u9fff]", report)),
        "body_citation_nums": body_cites,
        "body_citation_count": len(body_cites),
        "reference_entry_count": len(ref_ids) or len(re.findall(r"\*\*\[(\d+)\]\*\*", refs)),
        "heading_count": len(headings),
        "has_truncated": "[truncated]" in report,
        "has_ref_anchors": bool(re.search(r'id="ref-\d+"', report)),
        "missing_refs": [
            n
            for n in body_cites
            if n not in set(ref_ids)
        ]
        if ref_ids
        else [],
    }


def quality_score(report_stats: dict, job_ok: bool) -> dict:
    """Lightweight rubric 1-5; human can override later. :-)"""
    score = 5
    notes = []
    if not job_ok:
        return {"score": 1, "notes": ["job_failed"]}
    if report_stats["report_chars"] < 800:
        score -= 2
        notes.append("report_too_short")
    if report_stats["heading_count"] < 3:
        score -= 1
        notes.append("few_headings")
    if report_stats["body_citation_count"] < 2:
        score -= 1
        notes.append("few_citations")
    if report_stats["missing_refs"]:
        score -= 1
        notes.append("incomplete_references")
    if report_stats["has_truncated"]:
        score -= 1
        notes.append("body_truncated")
    if not report_stats["has_ref_anchors"]:
        score -= 1
        notes.append("no_ref_anchors")
    return {"score": max(1, min(5, score)), "notes": notes}


def extract_metrics(job: dict, worker_log_slice: str) -> dict:
    created = _ts(job.get("created_at"))
    updated = _ts(job.get("updated_at"))
    started = _ts(job.get("started_at") or job.get("running_at"))
    # Fallback: first checkpoint / version bump isn't reliable; use log if needed
    status = job.get("status")
    result = job.get("result") or {}
    cost = result.get("cost") or {}
    report = result.get("report") or ""
    payload = job.get("payload") or {}
    events = cost.get("llm_events") or []

    event_types = Counter(e.get("type") for e in events if isinstance(e, dict))
    models = []
    for e in events:
        if not isinstance(e, dict):
            continue
        for k in ("model", "to_model", "from_model", "provider"):
            if e.get(k):
                models.append(f"{k}={e.get(k)}")
    model_mentions = Counter(models)

    # Heuristic scrape counts from worker logs for this job id
    jid = job.get("id") or ""
    scrape_from = len(re.findall(r"Scraping content from (\d+) URLs", worker_log_slice))
    scrape_complete = worker_log_slice.count("Scraping complete")
    scrape_timeouts = len(
        re.findall(r"timeout|TimeoutError|asyncio.TimeoutError", worker_log_slice, re.I)
    )
    embed_retry_lines = len(
        re.findall(r"Retrying langchain_community.embeddings", worker_log_slice)
    )
    qwen_max_in_plan = bool(
        re.search(
            r"(Planning the research|choose_agent|sub-quer|subtopic).{0,200}qwen-max|qwen-max.{0,200}(Planning|sub-quer|subtopic)",
            worker_log_slice,
            re.I | re.S,
        )
    )
    # Broader: any qwen-max mention before Writing report
    plan_section = worker_log_slice
    write_idx = plan_section.find("Writing report")
    if write_idx >= 0:
        before_write = plan_section[:write_idx]
    else:
        before_write = plan_section
    qwen_max_before_write = "qwen-max" in before_write.lower()

    queue_sec = None
    total_sec = None
    if created and updated:
        total_sec = round(updated - created, 2)
    if created and started:
        queue_sec = round(max(0.0, started - created), 2)
    elif created and total_sec is not None:
        # Approximate queue from first running stage if started_at missing
        queue_sec = None

    report_stats = analyze_report(report)
    q = quality_score(report_stats, status == "completed" and bool(report.strip()))

    return {
        "job_id": jid,
        "task": payload.get("task"),
        "status": status,
        "error": job.get("error"),
        "created_at": created,
        "started_at": started,
        "updated_at": updated,
        "queue_sec": queue_sec,
        "total_sec": total_sec,
        "searches": cost.get("searches"),
        "llm_calls": cost.get("llm_calls"),
        "retries": cost.get("retries"),
        "model_switches": cost.get("model_switches"),
        "embedding_switches": cost.get("embedding_switches") or [],
        "embedding_switch_count": len(cost.get("embedding_switches") or []),
        "rag_degraded": bool(cost.get("rag_degraded")),
        "scrape_failures": int(cost.get("scrape_failures") or 0),
        "search_unavailable": bool(cost.get("search_unavailable")),
        "event_types": dict(event_types),
        "model_field_mentions": dict(model_mentions),
        "llm_events": events,
        "scrape_batches_logged": scrape_from,
        "scrape_complete_logged": scrape_complete,
        "timeout_mentions_in_job_logs": scrape_timeouts,
        "embedding_retry_log_lines": embed_retry_lines,
        "qwen_max_before_writing_report": qwen_max_before_write,
        "qwen_max_near_planning_heuristic": qwen_max_in_plan,
        "report": report_stats,
        "auto_quality": q,
    }


def wait_job(job_id: str) -> dict:
    deadline = time.time() + MAX_WAIT_PER_JOB_SEC
    last = ""
    job = {}
    while time.time() < deadline:
        data = _get(f"http://localhost:3000/api/jobs/{job_id}")
        job = data.get("job") or data
        st = f"{job.get('status')}|{job.get('stage')}|{job.get('progress')}"
        if st != last:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {job_id[:8]} {st}", flush=True)
            last = st
        if job.get("status") in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(POLL_SEC)
    return job


def main() -> int:
    started_wall = datetime.now(timezone.utc)
    cutoff_epoch = started_wall.timestamp()
    since = started_wall.strftime("%Y-%m-%dT%H:%M:%S")
    print("=== PERF ACCEPTANCE MONITOR ===", flush=True)
    print(f"since={since} cutoff_epoch={cutoff_epoch}", flush=True)
    print(f"Please submit the FIXED question {TARGET_RUNS} times from the frontend:", flush=True)
    print(f'  "{FIXED_TASK_HINT}，控制在500字以内"', flush=True)
    print("Only jobs created AFTER this monitor start are recorded.", flush=True)
    print("Waiting for new jobs...", flush=True)

    known: set[str] = set(SEED_JOB_IDS)
    records: list[dict] = []
    need = max(0, TARGET_RUNS - SEED_RECORDED)
    print(
        f"Already recorded runs: {SEED_RECORDED}. Waiting for {need} more new jobs...",
        flush=True,
    )

    while len(records) < need:
        for jid in discover_job_ids_from_next_logs(since, known):
            known.add(jid)
            if not is_job_after_cutoff(jid, cutoff_epoch):
                print(f"(skip stale job {jid})", flush=True)
                continue
            print(f"\n>>> Captured job {jid}", flush=True)
            job = wait_job(jid)
            # Narrow worker logs to this job window
            log_slice = _docker_logs_since("research-worker", since)
            # Keep only lines around this job id when possible
            if jid in log_slice:
                parts = log_slice.split(jid)
                # take surrounding context chunks
                chunks = []
                for i, part in enumerate(parts):
                    if i == 0:
                        chunks.append(part[-2000:])
                    else:
                        chunks.append(jid + part[:8000])
                log_slice = "\n".join(chunks)[-40000:]
            metrics = extract_metrics(job, log_slice)
            records.append(metrics)
            run_no = SEED_RECORDED + len(records)
            run_path = OUT_DIR / f"run_{run_no}_{jid}.json"
            metrics["run"] = run_no
            run_path.write_text(
                json.dumps(metrics, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        "run": run_no,
                        "status": metrics["status"],
                        "total_sec": metrics["total_sec"],
                        "queue_sec": metrics["queue_sec"],
                        "searches": metrics["searches"],
                        "scrape_failures": metrics["scrape_failures"],
                        "embedding_switch_count": metrics["embedding_switch_count"],
                        "rag_degraded": metrics["rag_degraded"],
                        "embedding_retry_log_lines": metrics["embedding_retry_log_lines"],
                        "llm_calls": metrics["llm_calls"],
                        "retries": metrics["retries"],
                        "qwen_max_before_writing": metrics["qwen_max_before_writing_report"],
                        "citations": metrics["report"]["body_citation_count"],
                        "refs": metrics["report"]["reference_entry_count"],
                        "chars": metrics["report"]["report_chars"],
                        "auto_quality": metrics["auto_quality"]["score"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if len(records) >= need:
                break
        if len(records) < need:
            time.sleep(3)

    # Merge seed run file if present. :-)
    seed_files = sorted(OUT_DIR.glob("run_1_*.json"))
    all_runs: list[dict] = []
    for p in seed_files:
        try:
            all_runs.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    all_runs.extend(records)

    summary = {
        "fixed_task_hint": FIXED_TASK_HINT,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "runs": all_runs,
        "aggregates": {
            "total_sec": [r.get("total_sec") for r in all_runs],
            "queue_sec": [r.get("queue_sec") for r in all_runs],
            "rag_degraded": [r.get("rag_degraded") for r in all_runs],
            "embedding_switch_count": [r.get("embedding_switch_count") for r in all_runs],
            "embedding_retry_log_lines": [
                r.get("embedding_retry_log_lines") for r in all_runs
            ],
            "scrape_failures": [r.get("scrape_failures") for r in all_runs],
            "qwen_max_before_writing": [
                r.get("qwen_max_before_writing_report") for r in all_runs
            ],
            "auto_quality": [r.get("auto_quality", {}).get("score") for r in all_runs],
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {SUMMARY_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
