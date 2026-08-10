"""Worker runtime helpers: heartbeat, cancel checks, budgets, checkpoints."""

from __future__ import annotations

import asyncio
import contextvars
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SEC = float(os.getenv("RESEARCH_HEARTBEAT_INTERVAL_SEC", "15"))

_abort_runtime: contextvars.ContextVar[Optional["JobRuntime"]] = contextvars.ContextVar(
    "research_abort_runtime", default=None
)


class JobCancelled(Exception):
    """Raised when cancel_requested is observed mid-run."""


def get_abort_runtime() -> Optional["JobRuntime"]:
    return _abort_runtime.get()


def set_abort_runtime(runtime: Optional["JobRuntime"]):
    return _abort_runtime.set(runtime)


def reset_abort_runtime(token) -> None:
    _abort_runtime.reset(token)


async def check_abort(where: str = "") -> None:
    """Cooperative abort used across stream_output / LLM / search / scrape."""
    runtime = _abort_runtime.get()
    if runtime is not None:
        await runtime.abort_check(where)


class JobRuntime:
    def __init__(
        self,
        job_id: str,
        worker_id: str,
        version: int,
        tenant_id: str = "anonymous",
        budget=None,
    ):
        self.job_id = job_id
        self.worker_id = worker_id
        self.version = version
        self.tenant_id = tenant_id
        self.budget = budget
        self._hb_task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self.cancel_seen = False
        self._ctx_token = None
        # Traceability: model switches / retries / continuations / chapter events
        self.llm_trace: list[dict[str, Any]] = []
        # Dependency degradations (search / scrape / embedding / rag)
        self.degradations: dict[str, Any] = {
            "search_unavailable": False,
            "search_keys_used": [],
            "search_keys_failed": [],
            "scrape_failures": 0,
            "scrape_failure_samples": [],
            "embedding_switches": [],
            "rag_degraded": False,
            "reasons": [],
        }

    def install(self) -> None:
        self._ctx_token = set_abort_runtime(self)

    def uninstall(self) -> None:
        if self._ctx_token is not None:
            reset_abort_runtime(self._ctx_token)
            self._ctx_token = None

    async def start_heartbeat(self) -> None:
        self._hb_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        self._stop.set()
        if self._hb_task:
            self._hb_task.cancel()
            try:
                await self._hb_task
            except asyncio.CancelledError:
                pass
            self._hb_task = None

    async def _heartbeat_loop(self) -> None:
        from jobs import update_job_heartbeat

        while not self._stop.is_set():
            try:
                ok = await update_job_heartbeat(
                    self.job_id, self.worker_id, self.version
                )
                if ok:
                    from jobs import get_job

                    job = await get_job(self.job_id)
                    if job and job.get("version"):
                        self.version = int(job["version"])
                else:
                    from jobs import get_job

                    job = await get_job(self.job_id)
                    if not job or job.get("worker_id") != self.worker_id:
                        logger.error(
                            "Heartbeat lost ownership of job %s — stopping", self.job_id
                        )
                        self.cancel_seen = True
                        return
                    self.version = int(job.get("version") or self.version)
                    ok2 = await update_job_heartbeat(
                        self.job_id, self.worker_id, self.version
                    )
                    if ok2:
                        job = await get_job(self.job_id)
                        if job and job.get("version"):
                            self.version = int(job["version"])
                    else:
                        logger.warning(
                            "Heartbeat update failed for %s after refresh", self.job_id
                        )
            except Exception as exc:
                logger.warning(
                    "Heartbeat update failed for %s (will retry): %s", self.job_id, exc
                )
            try:
                from jobs.slots import refresh_slot_lease

                await refresh_slot_lease(self.job_id)
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=HEARTBEAT_INTERVAL_SEC)
            except asyncio.TimeoutError:
                continue

    async def check_cancel(self, where: str = "") -> None:
        from jobs import get_job, update_job

        job = await get_job(self.job_id)
        if not job:
            return
        status = job.get("status")
        if status in ("cancel_requested", "cancelling", "cancelled"):
            self.cancel_seen = True
            if status == "cancel_requested":
                await update_job(
                    self.job_id,
                    status="cancelling",
                    progress=f"cancelling_at_{where or 'checkpoint'}",
                    last_error_code="cancelled",
                    tenant_id=self.tenant_id,
                    worker_id=self.worker_id,
                    expected_version=self.version,
                )
            raise JobCancelled(f"cancel_requested at {where}")

    async def abort_check(self, where: str = "") -> None:
        """Cancel first, then soft ownership loss."""
        if self.cancel_seen:
            raise JobCancelled(f"cancel_seen at {where}")
        await self.check_cancel(where)

    def register_search(self, n: int = 1, where: str = "search") -> None:
        if self.budget is not None:
            self.budget.register_search(n, where=where)

    def register_llm_call(self, where: str = "llm") -> None:
        if self.budget is not None:
            self.budget.register_llm_call(where=where)

    def record_llm_event(self, event_type: str, **fields: Any) -> None:
        """Append a tracing event (model_switch / retry / continue / truncate)."""
        entry = {
            "type": event_type,
            "ts": time.time(),
            **{k: v for k, v in fields.items() if v is not None},
        }
        self.llm_trace.append(entry)
        # Cap memory for long jobs
        if len(self.llm_trace) > 200:
            self.llm_trace = self.llm_trace[-150:]

    def record_degradation(self, subsystem: str, reason: str, **fields: Any) -> None:
        """Record search/scrape/embedding degrade for cost + checkpoint."""
        reason_s = (reason or "")[:300]
        entry = {
            "subsystem": subsystem,
            "reason": reason_s,
            "ts": time.time(),
            **{k: v for k, v in fields.items() if v is not None},
        }
        reasons = list(self.degradations.get("reasons") or [])
        reasons.append(entry)
        self.degradations["reasons"] = reasons[-40:]

        if subsystem == "search":
            self.degradations["search_unavailable"] = bool(
                fields.get("unavailable", True)
            )
            if fields.get("key_used"):
                used = list(self.degradations.get("search_keys_used") or [])
                if fields["key_used"] not in used:
                    used.append(fields["key_used"])
                self.degradations["search_keys_used"] = used[-10:]
            if fields.get("key_failed"):
                failed = list(self.degradations.get("search_keys_failed") or [])
                if fields["key_failed"] not in failed:
                    failed.append(fields["key_failed"])
                self.degradations["search_keys_failed"] = failed[-10:]
        elif subsystem == "scrape":
            self.degradations["scrape_failures"] = int(
                self.degradations.get("scrape_failures") or 0
            ) + int(fields.get("count") or 1)
            samples = list(self.degradations.get("scrape_failure_samples") or [])
            samples.append(
                {
                    "url": fields.get("url"),
                    "reason": reason_s,
                    "quality": fields.get("quality"),
                }
            )
            self.degradations["scrape_failure_samples"] = samples[-20:]
        elif subsystem in ("embedding", "rag"):
            if fields.get("from_model") or fields.get("to_model"):
                switches = list(self.degradations.get("embedding_switches") or [])
                switches.append(
                    {
                        "from": fields.get("from_model"),
                        "to": fields.get("to_model"),
                        "reason": reason_s,
                    }
                )
                self.degradations["embedding_switches"] = switches[-10:]
            if fields.get("rag_degraded") or subsystem == "rag":
                self.degradations["rag_degraded"] = True

        self.record_llm_event(f"degrade_{subsystem}", reason=reason_s, **fields)

    def degradations_snapshot(self) -> dict[str, Any]:
        return dict(self.degradations)

    def cost_trace(self) -> dict[str, Any]:
        """Summary suitable for Job.result.cost."""
        events = list(self.llm_trace)
        deg = self.degradations_snapshot()
        return {
            "model_switches": sum(1 for e in events if e.get("type") == "model_switch"),
            "retries": sum(1 for e in events if e.get("type") == "retry"),
            "continuations": sum(1 for e in events if e.get("type") == "continue"),
            "truncations": sum(1 for e in events if e.get("type") == "truncate"),
            "chapter_retries": sum(
                1 for e in events if e.get("type") == "chapter_retry"
            ),
            "llm_events": events[-80:],
            "search_unavailable": bool(deg.get("search_unavailable")),
            "search_keys_used": deg.get("search_keys_used") or [],
            "search_keys_failed": deg.get("search_keys_failed") or [],
            "scrape_failures": int(deg.get("scrape_failures") or 0),
            "embedding_switches": deg.get("embedding_switches") or [],
            "rag_degraded": bool(deg.get("rag_degraded")),
            "degrade_reasons": deg.get("reasons") or [],
        }

    async def save_checkpoint(self, **fields: Any) -> None:
        from jobs import get_job, update_job

        job = await get_job(self.job_id) or {}
        cp = dict(job.get("checkpoint_json") or {})
        cp.update(fields)
        if self.budget is not None:
            cp["budget"] = self.budget.snapshot()
        if self.llm_trace:
            cp["llm_trace"] = self.llm_trace[-80:]
        if self.degradations:
            # Merge degradations rather than clobber caller-provided snapshot
            existing = dict(cp.get("degradations") or {})
            existing.update(self.degradations_snapshot())
            cp["degradations"] = existing
        await update_job(
            self.job_id,
            checkpoint_json=cp,
            tenant_id=self.tenant_id,
            worker_id=self.worker_id,
        )


class CancellingProgressSink:
    """Wraps JobProgressSink with cancel checks + stage updates."""

    def __init__(self, inner, runtime: JobRuntime):
        self._inner = inner
        self.runtime = runtime
        self.log_file = getattr(inner, "log_file", "")

    async def send_json(self, data: dict) -> None:
        await self.runtime.abort_check(where=str(data.get("content") or "stream"))
        await self._inner.send_json(data)
