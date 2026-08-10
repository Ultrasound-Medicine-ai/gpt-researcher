"""Trusted report pipeline: plan → evidence/claim → constrained write → audit."""

from trusted_report.execution import ExecutionTrace, execute_report_job
from trusted_report.flags import (
    trusted_report_fallback_to_legacy,
    trusted_report_pipeline_enabled,
    trusted_report_shadow_mode,
)
from trusted_report.gray import should_use_trusted_pipeline
from trusted_report.models import CitationAuditFailed, TrustOutcome
from trusted_report.pipeline import (
    apply_trust_policy,
    deliver_with_policy,
    run_trusted_write_pipeline,
)

__all__ = [
    "trusted_report_pipeline_enabled",
    "trusted_report_shadow_mode",
    "trusted_report_fallback_to_legacy",
    "should_use_trusted_pipeline",
    "CitationAuditFailed",
    "TrustOutcome",
    "ExecutionTrace",
    "execute_report_job",
    "apply_trust_policy",
    "deliver_with_policy",
    "run_trusted_write_pipeline",
]
