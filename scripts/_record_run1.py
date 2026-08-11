import json
import re
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path

jid = "bbc6a5ba-9126-4ead-bcec-b3892abf17d2"
job = json.loads(
    urllib.request.urlopen(f"http://localhost:3000/api/jobs/{jid}", timeout=30)
    .read()
    .decode()
)["job"]


def ts(v):
    if v is None:
        return None
    x = float(v)
    return x / 1000 if x > 1e12 else x


created, started, updated = (
    ts(job.get("created_at")),
    ts(job.get("started_at")),
    ts(job.get("updated_at")),
)
result = job.get("result") or {}
cost = result.get("cost") or {}
report = result.get("report") or ""
events = cost.get("llm_events") or []
event_types = Counter(e.get("type") for e in events if isinstance(e, dict))
models = []
for e in events:
    if not isinstance(e, dict):
        continue
    for k in ("model", "to_model", "from_model"):
        if e.get(k):
            models.append(f"{k}={e.get(k)}")

body = report.split("参考文献")[0] if "参考文献" in report else report
body_cites = sorted({int(x) for x in re.findall(r"\[(\d+)\]", body)})
ref_ids = [int(x) for x in re.findall(r'id="ref-(\d+)"', report)]
headings = re.findall(r"^#{1,3}\s+.+$", report, flags=re.M)

log = subprocess.run(
    [
        "docker",
        "compose",
        "logs",
        "--no-color",
        "--since",
        "30m",
        "research-worker",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"F:\agent\gpt-researcher",
).stdout
idx = log.find(jid)
slice_ = log[max(0, idx - 500) : idx + 15000] if idx >= 0 else log[-20000:]
embed_retry = len(re.findall(r"Retrying langchain_community.embeddings", slice_))
write_idx = slice_.find("Writing report")
before = slice_[:write_idx] if write_idx >= 0 else slice_
qwen_max_before = "qwen-max" in before.lower()
scrape_batches = len(re.findall(r"Scraping content from (\d+) URLs", slice_))
scrape_complete = slice_.count("Scraping complete")
timeouts = len(re.findall(r"timeout|TimeoutError", slice_, re.I))

queue = round((started - created), 2) if created and started else None
total = round((updated - created), 2) if created and updated else None
missing = [n for n in body_cites if n not in set(ref_ids)]
score = 5
notes = []
if len(report) < 800:
    score -= 2
    notes.append("short")
if len(headings) < 3:
    score -= 1
    notes.append("few_headings")
if len(body_cites) < 2:
    score -= 1
    notes.append("few_cites")
if missing:
    score -= 1
    notes.append("missing_refs")
if "[truncated]" in report:
    score -= 1
    notes.append("truncated")

rec = {
    "run": 1,
    "job_id": jid,
    "task": (job.get("payload") or {}).get("task"),
    "status": job.get("status"),
    "queue_sec": queue,
    "total_sec": total,
    "created_at": created,
    "started_at": started,
    "updated_at": updated,
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
    "model_field_mentions": dict(Counter(models)),
    "llm_events": events,
    "scrape_batches_logged": scrape_batches,
    "scrape_complete_logged": scrape_complete,
    "timeout_mentions_in_job_logs": timeouts,
    "embedding_retry_log_lines": embed_retry,
    "qwen_max_before_writing_report": qwen_max_before,
    "report": {
        "report_chars": len(report),
        "body_citation_count": len(body_cites),
        "body_citation_nums": body_cites,
        "reference_entry_count": len(ref_ids),
        "heading_count": len(headings),
        "has_truncated": "[truncated]" in report,
        "has_ref_anchors": bool(ref_ids),
        "missing_refs": missing,
    },
    "auto_quality": {"score": max(1, score), "notes": notes},
    "stage_log_estimate_sec": {
        "planning": 22,
        "scrape": 11,
        "writing": 45,
        "worker_arq_sec": 135.41,
    },
}
out = Path(r"F:\agent\gpt-researcher\outputs\perf_acceptance")
out.mkdir(parents=True, exist_ok=True)
(out / f"run_1_{jid}.json").write_text(
    json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {
            "run": 1,
            "job_id": jid,
            "status": rec["status"],
            "queue_sec": rec["queue_sec"],
            "total_sec": rec["total_sec"],
            "searches": rec["searches"],
            "scrape_failures": rec["scrape_failures"],
            "embedding_switch_count": rec["embedding_switch_count"],
            "rag_degraded": rec["rag_degraded"],
            "embedding_retry_log_lines": rec["embedding_retry_log_lines"],
            "llm_calls": rec["llm_calls"],
            "retries": rec["retries"],
            "model_switches": rec["model_switches"],
            "qwen_max_before_writing": rec["qwen_max_before_writing_report"],
            "citations": rec["report"]["body_citation_count"],
            "refs": rec["report"]["reference_entry_count"],
            "chars": rec["report"]["report_chars"],
            "auto_quality": rec["auto_quality"],
            "stages": rec["stage_log_estimate_sec"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
