"""Job progress fan-out via Redis pub/sub (uses shared pool when available)."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, AsyncIterator, Dict

logger = logging.getLogger(__name__)


def job_events_channel(job_id: str, tenant_id: str = "anonymous") -> str:
    from security import redis_key

    return redis_key(tenant_id or "anonymous", "job", job_id, "events")


async def publish_job_event(
    job_id: str,
    event: Dict[str, Any],
    *,
    tenant_id: str = "anonymous",
) -> None:
    """Best-effort publish via shared pool; never raises into research path."""
    try:
        from jobs.redis_pool import ensure_arq_pool, get_redis_url

        if not get_redis_url():
            return
        redis = await ensure_arq_pool()
        if redis is None:
            return
        payload = {**event, "job_id": job_id, "ts": int(time.time() * 1000)}
        await redis.publish(
            job_events_channel(job_id, tenant_id),
            json.dumps(payload, ensure_ascii=False, default=str),
        )
    except Exception as exc:
        logger.debug("publish_job_event skipped: %s", exc)


class JobProgressSink:
    """Websocket-compatible sink: send_json → Redis events + local log file."""

    def __init__(self, job_id: str, task: str, tenant_id: str = "anonymous"):
        self.job_id = job_id
        self.tenant_id = tenant_id or "anonymous"
        sanitized = "".join(c if c.isalnum() or c in "-_" else "_" for c in task[:40])
        self.log_file = os.path.join(
            "outputs", f"job_{job_id}_{int(time.time())}_{sanitized}.json"
        )
        self.timestamp = datetime.now().isoformat()
        os.makedirs("outputs", exist_ok=True)
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": self.timestamp,
                    "job_id": job_id,
                    "events": [],
                    "content": {
                        "query": task,
                        "sources": [],
                        "context": [],
                        "report": "",
                        "costs": 0.0,
                    },
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    async def send_json(self, data: Dict[str, Any]) -> None:
        # Map log content hints → stage updates (best-effort)
        try:
            content = str(data.get("content") or "")
            stage = None
            if content in ("planning_research", "mcp_init", "subtopics_generated"):
                stage = "planning"
            elif content in (
                "scraping_urls",
                "scraping_content",
                "scraping_complete",
                "added_source_url",
            ):
                stage = "researching"
            elif content in ("writing_report", "report_written", "generating_report"):
                stage = "writing"
            if stage:
                from jobs import update_job

                await update_job(
                    self.job_id, stage=stage, progress=content, tenant_id=self.tenant_id
                )
        except Exception:
            pass

        await publish_job_event(self.job_id, data, tenant_id=self.tenant_id)
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
            if data.get("type") == "logs":
                log_data["events"].append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "type": "event",
                        "data": data,
                    }
                )
            else:
                log_data["content"].update(data)
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.debug("JobProgressSink log write failed: %s", exc)


async def subscribe_job_events(
    job_id: str,
    *,
    tenant_id: str = "anonymous",
    stop_when_terminal: bool = True,
) -> AsyncIterator[Dict[str, Any]]:
    """Optional SSE/WS stream. Primary UI path is HTTP polling."""
    from jobs import TERMINAL_STATUSES, get_job
    import asyncio

    last_status = None
    last_progress = None
    while True:
        job = await get_job(job_id, tenant_id=tenant_id)
        if job is None:
            yield {"type": "error", "content": "error", "output": "Job not found"}
            return
        status = job.get("status")
        progress = job.get("progress")
        stage = job.get("stage")
        if status != last_status or progress != last_progress:
            last_status, last_progress = status, progress
            yield {
                "type": "job_status",
                "content": "job_status",
                "output": {
                    "job_id": job_id,
                    "status": status,
                    "stage": stage,
                    "progress": progress,
                    "error": job.get("error"),
                },
            }
        if stop_when_terminal and status in TERMINAL_STATUSES:
            if status == "completed" and job.get("result"):
                result = job["result"]
                report = result.get("report") or ""
                if report:
                    yield {
                        "type": "report_complete",
                        "content": "report",
                        "output": report,
                    }
                if result.get("file_paths"):
                    yield {"type": "path", "output": result["file_paths"]}
            elif status == "failed":
                yield {
                    "type": "error",
                    "content": "error",
                    "output": job.get("error") or "Research job failed",
                }
            return
        await asyncio.sleep(1.0)
