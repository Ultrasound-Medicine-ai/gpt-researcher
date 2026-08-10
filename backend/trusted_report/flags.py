"""Feature flags for the trusted report pipeline bypass."""

from __future__ import annotations

import os


def _truthy(name: str, default: str = "false") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def trusted_report_pipeline_enabled() -> bool:
    """Primary switch. Also accepts legacy ENABLE_TRUSTED_REPORT_PIPELINE."""
    if os.getenv("TRUSTED_REPORT_PIPELINE_ENABLED") is not None:
        return _truthy("TRUSTED_REPORT_PIPELINE_ENABLED", "false")
    return _truthy("ENABLE_TRUSTED_REPORT_PIPELINE", "false")


def trusted_report_shadow_mode() -> bool:
    return _truthy("TRUSTED_REPORT_SHADOW_MODE", "false")


def trusted_report_fallback_to_legacy() -> bool:
    return _truthy("TRUSTED_REPORT_FALLBACK_TO_LEGACY", "true")


def env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return max(minimum, int(raw)) if raw else default
    except ValueError:
        return default
