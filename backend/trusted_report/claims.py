"""Claim generation + programmatic validation."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

from trusted_report.llm import call_llm_json
from trusted_report.models import ClaimItem, EvidenceItem, OutlineSection, as_str_list
from trusted_report import prompts

logger = logging.getLogger(__name__)

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?%?")
_DATE_RE = re.compile(
    r"\b(?:19|20)\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
)


def statement_contains_number(text: str) -> bool:
    return bool(_NUM_RE.search(text or ""))


def statement_contains_date(text: str) -> bool:
    return bool(_DATE_RE.search(text or ""))


def numbers_supported_by_evidence(statement: str, evidences: list[EvidenceItem]) -> bool:
    nums = _NUM_RE.findall(statement or "")
    if not nums:
        return True
    blob = " ".join(e.quote for e in evidences)
    for n in nums:
        if n not in blob and n.replace(",", "") not in blob.replace(",", ""):
            return False
    return True


def validate_claims(
    raw_claims: list[dict[str, Any]],
    evidence: list[EvidenceItem],
    *,
    section_id: str,
    tenant_id: str,
    session_id: Optional[str],
) -> tuple[list[ClaimItem], list[str], int]:
    """
    Programmatic claim gate.
    Returns (accepted_or_uncertainty, unsupported_ids, cross_scope_violations).
    """
    by_eid = {e.evidence_id: e for e in evidence}
    out: list[ClaimItem] = []
    unsupported: list[str] = []
    cross_scope = 0

    for i, raw in enumerate(raw_claims):
        cid = str(raw.get("claim_id") or f"cl_{section_id}_{i+1:03d}")
        statement = str(raw.get("statement") or "").strip()
        if not statement:
            continue
        claim_type = str(raw.get("claim_type") or "fact").lower()
        eids = [x for x in as_str_list(raw.get("evidence_ids")) if x in by_eid]
        bound = [by_eid[e] for e in eids]

        for e in bound:
            if e.tenant_id and e.tenant_id != tenant_id:
                cross_scope += 1
                eids = []
                bound = []
                break
            if session_id and e.session_id and str(e.session_id) != str(session_id):
                cross_scope += 1
                eids = []
                bound = []
                break

        contains_number = bool(raw.get("contains_number")) or statement_contains_number(statement)
        contains_date = bool(raw.get("contains_date")) or statement_contains_date(statement)
        requires = bool(raw.get("requires_citation", True))
        if claim_type in ("fact", "comparison") or contains_number or contains_date:
            requires = True

        if requires and not eids:
            if claim_type == "uncertainty":
                out.append(
                    ClaimItem(
                        claim_id=cid,
                        section_id=section_id,
                        statement=statement,
                        claim_type="uncertainty",
                        evidence_ids=[],
                        requires_citation=False,
                        contains_number=contains_number,
                        contains_date=contains_date,
                        confidence="low",
                        caveat=str(raw.get("caveat") or "insufficient evidence"),
                    )
                )
            else:
                unsupported.append(cid)
            continue

        if contains_number and bound and not numbers_supported_by_evidence(statement, bound):
            unsupported.append(cid)
            continue

        sources = {(e.document_id or e.url or e.chunk_id) for e in bound}
        single = contains_number and len(sources) < 2
        caveat = str(raw.get("caveat") or "")
        if single:
            caveat = (caveat + " ; single-source numeric claim").strip(" ;")

        out.append(
            ClaimItem(
                claim_id=cid,
                section_id=section_id,
                statement=statement,
                claim_type=claim_type,
                evidence_ids=eids,
                requires_citation=requires,
                contains_number=contains_number,
                contains_date=contains_date,
                confidence=str(raw.get("confidence") or "medium"),
                caveat=caveat,
                single_source=single,
            )
        )
    return out, unsupported, cross_scope


async def build_section_claims(
    section: OutlineSection,
    evidence: list[EvidenceItem],
    *,
    tenant_id: str,
    session_id: Optional[str] = None,
    llm_call: Optional[Callable[..., Any]] = None,
) -> tuple[list[ClaimItem], list[str], int]:
    if not evidence:
        return [], [], 0
    try:
        data = await call_llm_json(
            system=prompts.claim_system(),
            user=prompts.claim_user(
                section_id=section.section_id,
                purpose=section.purpose,
                questions=section.questions_to_answer,
                evidence=[e.to_dict() for e in evidence],
                expected_types=section.expected_claim_types or ["fact", "analysis"],
            ),
            llm_call=llm_call,
        )
        raw = list(data.get("claims") or [])
    except Exception as exc:
        logger.warning("Claim LLM failed: %s", exc)
        raw = []
    return validate_claims(
        raw,
        evidence,
        section_id=section.section_id,
        tenant_id=tenant_id,
        session_id=session_id,
    )
