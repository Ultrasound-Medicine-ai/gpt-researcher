"""Programmatic citation injection and audit (model numbers are never trusted)."""

from __future__ import annotations

import re
from typing import Optional

from trusted_report.models import AuditResult, ClaimItem, EvidenceItem
from trusted_report.writer import CLAIM_MARKER_RE, extract_claim_markers


def build_citation_maps(
    report_with_markers: str,
    claims: list[ClaimItem],
    evidence: list[EvidenceItem],
) -> tuple[dict[str, list[int]], dict[int, EvidenceItem], list[str]]:
    """
    Map claim markers in document order to citation numbers.
    Returns (claim_id -> [nums], num -> EvidenceItem, ordered claim ids seen).
    """
    by_claim = {c.claim_id: c for c in claims}
    by_eid = {e.evidence_id: e for e in evidence}
    claim_to_nums: dict[str, list[int]] = {}
    num_to_ev: dict[int, EvidenceItem] = {}
    seen_ev: dict[str, int] = {}
    next_num = 1
    ordered_claims: list[str] = []

    for cid in extract_claim_markers(report_with_markers):
        if cid not in by_claim:
            continue
        if cid not in ordered_claims:
            ordered_claims.append(cid)
        claim = by_claim[cid]
        nums: list[int] = []
        for eid in claim.evidence_ids:
            ev = by_eid.get(eid)
            if not ev:
                continue
            if eid not in seen_ev:
                seen_ev[eid] = next_num
                num_to_ev[next_num] = ev
                next_num += 1
            nums.append(seen_ev[eid])
        claim_to_nums[cid] = nums
    return claim_to_nums, num_to_ev, ordered_claims


def inject_citations(
    report_with_markers: str,
    claims: list[ClaimItem],
    evidence: list[EvidenceItem],
) -> tuple[str, dict[int, EvidenceItem]]:
    claim_to_nums, num_to_ev, _ = build_citation_maps(report_with_markers, claims, evidence)

    def _repl(match: re.Match) -> str:
        cid = match.group(1)
        nums = claim_to_nums.get(cid) or []
        if not nums:
            return ""
        return "".join(f"[{n}]" for n in nums)

    body = CLAIM_MARKER_RE.sub(_repl, report_with_markers or "")
    if num_to_ev:
        lines = ["", "## References", ""]
        for n in sorted(num_to_ev):
            ev = num_to_ev[n]
            page = f", p.{ev.page}" if ev.page is not None else ""
            url = f" — {ev.url}" if ev.url else ""
            lines.append(f"[{n}] {ev.source_title or 'Source'}{page}{url}")
            lines.append(f"> {ev.quote}")
            lines.append("")
        body = body.rstrip() + "\n" + "\n".join(lines)
    return body, num_to_ev


def audit_report(
    report_with_markers: str,
    claims: list[ClaimItem],
    evidence: list[EvidenceItem],
    *,
    cross_scope_violations: int = 0,
    min_coverage: float = 0.85,
) -> AuditResult:
    by_claim = {c.claim_id: c for c in claims if not c.rejected}
    required = [c for c in by_claim.values() if c.requires_citation]
    markers = set(extract_claim_markers(report_with_markers))
    unsupported: list[str] = []
    for c in required:
        if c.claim_id not in markers:
            unsupported.append(c.claim_id)
            continue
        if not c.evidence_ids:
            unsupported.append(c.claim_id)

    # Evidence deletion / orphan: claim cites missing evidence
    eids = {e.evidence_id for e in evidence}
    for c in required:
        if c.claim_id in unsupported:
            continue
        if any(eid not in eids for eid in c.evidence_ids):
            unsupported.append(c.claim_id)

    single_numeric = [
        c.claim_id for c in by_claim.values() if c.contains_number and c.single_source
    ]
    total = len(required) or len(by_claim)
    supported = max(0, total - len(set(unsupported)))
    coverage = (supported / total) if total else 1.0
    failed = (
        coverage < min_coverage
        or bool(unsupported)
        or cross_scope_violations > 0
    )
    return AuditResult(
        citation_coverage=round(coverage, 4),
        total_claims=total,
        supported_claims=supported,
        unsupported_claims=sorted(set(unsupported)),
        single_source_numeric_claims=single_numeric,
        cross_scope_violations=cross_scope_violations,
        citation_audit_failed=failed,
    )


def trace_claim_to_source(
    claim_id: str,
    claims: list[ClaimItem],
    evidence: list[EvidenceItem],
) -> Optional[dict]:
    claim = next((c for c in claims if c.claim_id == claim_id), None)
    if not claim:
        return None
    evs = [e for e in evidence if e.evidence_id in claim.evidence_ids]
    return {
        "claim": claim.to_dict(),
        "evidence": [e.to_dict() for e in evs],
        "chunks": [
            {
                "chunk_id": e.chunk_id,
                "parent_chunk_id": e.parent_chunk_id,
                "page": e.page,
                "url": e.url,
                "quote": e.quote,
            }
            for e in evs
        ],
    }
