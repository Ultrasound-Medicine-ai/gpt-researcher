"""Percentage rollout + automatic kill-switch for trusted pipeline."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Optional

from trusted_report.flags import (
    env_int,
    trusted_report_pipeline_enabled,
)

logger = logging.getLogger(__name__)

# Process-local kill switch (also mirrored to env for workers that re-read flags)
_KILL_UNTIL: float = 0.0
_ANOMALY_STREAK: int = 0


def gray_percent() -> int:
    """0–100. Default 0 = only explicit ENABLED without percent gate...

    When TRUSTED_REPORT_GRAY_PERCENT is unset, behave as 100% of enabled traffic
    (flag alone controls). When set (e.g. 5), only that % of sample keys
    enter trusted/shadow (others stay legacy even if ENABLED).
    """
    raw = (os.getenv("TRUSTED_REPORT_GRAY_PERCENT") or "").strip()
    if raw == "":
        return 100
    try:
        return max(0, min(100, int(raw)))
    except ValueError:
        return 0


def _stable_bucket(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def kill_switch_active() -> bool:
    return time.time() < _KILL_UNTIL


def activate_kill_switch(reason: str, *, minutes: Optional[int] = None) -> None:
    global _KILL_UNTIL
    mins = minutes if minutes is not None else env_int(
        "TRUSTED_REPORT_KILL_MINUTES", 60, minimum=1
    )
    _KILL_UNTIL = time.time() + mins * 60
    os.environ["TRUSTED_REPORT_KILL_SWITCH"] = "1"
    logger.error(
        "Trusted report kill-switch ON for %s min — reason=%s", mins, reason[:300]
    )


def clear_kill_switch() -> None:
    global _KILL_UNTIL, _ANOMALY_STREAK
    _KILL_UNTIL = 0.0
    _ANOMALY_STREAK = 0
    os.environ.pop("TRUSTED_REPORT_KILL_SWITCH", None)


def record_release_anomaly(failed: bool) -> None:
    """Trip kill-switch after N consecutive release-gate failures."""
    global _ANOMALY_STREAK
    threshold = env_int("TRUSTED_REPORT_ANOMALY_STREAK", 3, minimum=1)
    if not failed:
        _ANOMALY_STREAK = 0
        return
    _ANOMALY_STREAK += 1
    if _ANOMALY_STREAK >= threshold:
        activate_kill_switch(f"anomaly_streak={_ANOMALY_STREAK}")


def sample_bucket_key(
    *,
    sample_key: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """Prefer per-task key (job/session) so anonymous traffic can still sample ~N%. :-)"""
    sk = (sample_key or "").strip()
    if sk:
        return sk
    return f"{tenant_id or 'anonymous'}:{user_id or 'anonymous'}"


def allow_force_sample() -> bool:
    """Ops/review only: payload may force a task into trusted/shadow. :-)"""
    return (os.getenv("TRUSTED_REPORT_ALLOW_FORCE_SAMPLE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def should_use_trusted_pipeline(
    *,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    sample_key: Optional[str] = None,
    force: bool = False,
) -> bool:
    """
    Effective enablement for trusted primary OR shadow dual-write.

    Order: kill-switch → master flag → (optional force) → gray percent bucket.
    Shadow does NOT bypass gray — both modes sample the same percent of tasks.
    """
    if (os.getenv("TRUSTED_REPORT_KILL_SWITCH") or "").strip() in (
        "1",
        "true",
        "yes",
        "on",
    ) or kill_switch_active():
        return False
    if not trusted_report_pipeline_enabled():
        return False
    if force and allow_force_sample():
        return True
    pct = gray_percent()
    if pct >= 100:
        return True
    if pct <= 0:
        return False
    key = sample_bucket_key(
        sample_key=sample_key, user_id=user_id, tenant_id=tenant_id
    )
    return _stable_bucket(key) < pct
