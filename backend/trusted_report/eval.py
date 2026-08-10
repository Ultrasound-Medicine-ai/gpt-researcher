"""Trusted report evaluation metrics and release gates."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from trusted_report.evidence import quote_in_source
from trusted_report.flags import env_int
from trusted_report.models import AuditResult, ClaimItem, EvidenceItem
from trusted_report.writer import extract_claim_markers as _extract


@dataclass
class EvalScores:
    citation_accuracy: float = 0.0  # quotes found in chunk texts when provided
    claim_support_rate: float = 0.0
    global_coherence: float = 0.0  # proxy: section marker continuity
    duplication_rate: float = 0.0
    fact_conflict_rate: float = 0.0
    citation_coverage: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReleaseGateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    scores: Optional[EvalScores] = None
    audit: Optional[AuditResult] = None
    p95_ms: Optional[float] = None
    cost_units: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": self.reasons,
            "scores": self.scores.to_dict() if self.scores else None,
            "audit": self.audit.to_dict() if self.audit else None,
            "p95_ms": self.p95_ms,
            "cost_units": self.cost_units,
        }


def _ngram_jaccard(a: str, b: str, n: int = 3) -> float:
    def grams(s: str) -> set[str]:
        s = re.sub(r"\s+", " ", s.lower()).strip()
        if len(s) < n:
            return {s}
        return {s[i : i + n] for i in range(len(s) - n + 1)}

    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def evaluate_trusted_report(
    *,
    report_with_markers: str,
    claims: list[ClaimItem],
    evidence: list[EvidenceItem],
    audit: AuditResult,
    chunk_texts: Optional[dict[str, str]] = None,
) -> EvalScores:
    """
    Offline-friendly metrics for the trusted eval set.

    chunk_texts: optional {chunk_id: original child content} for citation accuracy.
    """
    by_eid = {e.evidence_id: e for e in evidence}
    required = [c for c in claims if c.requires_citation and not c.rejected]
    supported = 0
    for c in required:
        if c.evidence_ids and all(eid in by_eid for eid in c.evidence_ids):
            supported += 1
    claim_support = (supported / len(required)) if required else 1.0

    # Citation accuracy vs provided chunk texts
    acc_ok = 0
    acc_total = 0
    if chunk_texts:
        for e in evidence:
            acc_total += 1
            src = chunk_texts.get(e.chunk_id) or ""
            if src and quote_in_source(e.quote, src):
                acc_ok += 1
        citation_acc = (acc_ok / acc_total) if acc_total else 1.0
    else:
        citation_acc = 1.0 if evidence else 0.0

    # Duplication: pairwise section-ish blocks
    blocks = [b.strip() for b in re.split(r"\n#{1,3}\s+", report_with_markers or "") if b.strip()]
    dup_pairs = 0
    pair_n = 0
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            pair_n += 1
            if _ngram_jaccard(blocks[i], blocks[j]) >= 0.55:
                dup_pairs += 1
    duplication = (dup_pairs / pair_n) if pair_n else 0.0

    # Fact conflict proxy: opposite polarity keywords across claims with numbers
    pos = ("增长", "上升", "提高", "increase", "grew", "growth")
    neg = ("下降", "下滑", "减少", "decline", "fell", "drop")
    has_pos = any(any(p in c.statement.lower() for p in pos) for c in claims)
    has_neg = any(any(n in c.statement.lower() for n in neg) for c in claims)
    # Conflict only if both polarities without uncertainty caveat
    conflict = 1.0 if (has_pos and has_neg and not any(c.claim_type == "uncertainty" for c in claims)) else 0.0

    markers = set(_extract(report_with_markers))
    coherence = 1.0
    if required:
        covered = sum(1 for c in required if c.claim_id in markers)
        coherence = covered / len(required)

    return EvalScores(
        citation_accuracy=round(citation_acc, 4),
        claim_support_rate=round(claim_support, 4),
        global_coherence=round(coherence, 4),
        duplication_rate=round(duplication, 4),
        fact_conflict_rate=round(conflict, 4),
        citation_coverage=float(audit.citation_coverage),
        details={
            "required_claims": len(required),
            "supported_claims": supported,
            "evidence_count": len(evidence),
        },
    )


def check_release_gates(
    *,
    audit: AuditResult,
    scores: EvalScores,
    duration_ms: Optional[float] = None,
    cost_units: Optional[float] = None,
) -> ReleaseGateResult:
    """
    Publish gates:
    - Audit PASS
    - citation coverage threshold
    - optional P95 latency / cost caps (env)
    """
    reasons: list[str] = []
    min_cov = env_int("TRUSTED_MIN_CITATION_COVERAGE_PCT", 85, minimum=1) / 100.0
    max_p95 = env_int("TRUSTED_RELEASE_MAX_P95_MS", 0, minimum=0)  # 0 = disabled
    max_cost = env_int("TRUSTED_RELEASE_MAX_COST_UNITS", 0, minimum=0)

    if audit.citation_audit_failed:
        reasons.append("audit_failed")
    if audit.citation_coverage < min_cov:
        reasons.append(f"coverage_below_{min_cov}")
    if scores.citation_accuracy < 0.9:
        reasons.append("citation_accuracy_below_0.9")
    if scores.claim_support_rate < 0.85:
        reasons.append("claim_support_below_0.85")
    if scores.duplication_rate > 0.35:
        reasons.append("duplication_too_high")
    if scores.fact_conflict_rate >= 1.0:
        reasons.append("unresolved_fact_conflict")
    if max_p95 and duration_ms is not None and duration_ms > max_p95:
        reasons.append(f"p95_above_{max_p95}ms")
    if max_cost and cost_units is not None and cost_units > max_cost:
        reasons.append(f"cost_above_{max_cost}")

    return ReleaseGateResult(
        passed=not reasons,
        reasons=reasons,
        scores=scores,
        audit=audit,
        p95_ms=duration_ms,
        cost_units=cost_units,
    )


def shadow_compare(
    *,
    legacy_report: str,
    trusted_report: str,
    legacy_ms: float,
    trusted_ms: float,
    legacy_cost: float = 0.0,
    trusted_cost: float = 0.0,
) -> dict[str, Any]:
    """Compare shadow dual-run quality proxies, latency, and cost."""
    leg_len = len(legacy_report or "")
    tru_len = len(trusted_report or "")
    overlap = _ngram_jaccard(legacy_report or "", trusted_report or "", n=5)
    return {
        "legacy_chars": leg_len,
        "trusted_chars": tru_len,
        "content_overlap": round(overlap, 4),
        "legacy_ms": legacy_ms,
        "trusted_ms": trusted_ms,
        "latency_delta_ms": round(trusted_ms - legacy_ms, 2),
        "legacy_cost": legacy_cost,
        "trusted_cost": trusted_cost,
        "cost_delta": round(trusted_cost - legacy_cost, 4),
        "trusted_has_citations": bool(re.search(r"\[\d+\]", trusted_report or "")),
        "legacy_has_citations": bool(re.search(r"\[\d+\]", legacy_report or "")),
    }
