"""Data models for trusted report pipeline artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional


ReportTrust = Literal["trusted", "legacy_unverified"]


def _safe_relevance(value: Any) -> float:
    """Accept numeric scores or common Chinese relevance labels. :-)"""
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    text = str(value).strip()
    try:
        return max(0.0, min(1.0, float(text)))
    except ValueError:
        labels = {
            "直接相关": 1.0,
            "高度相关": 0.9,
            "相关": 0.7,
            "部分相关": 0.5,
            "弱相关": 0.3,
            "不相关": 0.0,
            "无关": 0.0,
        }
        if text in labels:
            return labels[text]
        for label, score in labels.items():
            if label in text:
                return score
        return 0.0


def as_str_list(value: Any) -> list[str]:
    """Coerce LLM/JSON fields to list[str]; bool/scalar must not explode list(). :-)"""
    if value is None or value is False:
        return []
    if value is True:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, (list, tuple, set)):
        return [str(x) for x in value if x is not None and str(x).strip() != ""]
    return [str(value)]


@dataclass
class MapSection:
    parent_chunk_id: str
    heading: str
    position: int
    summary_or_excerpt: str
    child_count: int = 0


@dataclass
class DocumentMapEntry:
    document_id: str
    title: str
    source_type: str = "web"
    published_at: str = ""
    source_quality: str = ""
    sections: list[MapSection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutlineSection:
    section_id: str
    title: str
    purpose: str = ""
    questions_to_answer: list[str] = field(default_factory=list)
    depends_on_sections: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    expected_claim_types: list[str] = field(default_factory=list)


@dataclass
class ReportOutline:
    report_thesis: str = ""
    scope: str = ""
    time_range: str = ""
    sections: list[OutlineSection] = field(default_factory=list)
    cross_section_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportOutline":
        sections = [
            OutlineSection(
                section_id=str(s.get("section_id") or f"sec_{i}"),
                title=str(s.get("title") or f"Section {i}"),
                purpose=str(s.get("purpose") or ""),
                questions_to_answer=list(s.get("questions_to_answer") or []),
                depends_on_sections=list(s.get("depends_on_sections") or []),
                search_queries=list(s.get("search_queries") or []),
                expected_claim_types=list(s.get("expected_claim_types") or []),
            )
            for i, s in enumerate(data.get("sections") or [])
        ]
        return cls(
            report_thesis=str(data.get("report_thesis") or ""),
            scope=str(data.get("scope") or ""),
            time_range=str(data.get("time_range") or ""),
            sections=sections,
            cross_section_questions=list(data.get("cross_section_questions") or []),
        )


@dataclass
class EvidenceItem:
    evidence_id: str
    chunk_id: str
    parent_chunk_id: str = ""
    quote: str = ""
    source_title: str = ""
    url: str = ""
    page: Optional[int] = None
    published_at: str = ""
    source_quality: str = ""
    supports: list[str] = field(default_factory=list)
    relevance: float = 0.0
    document_id: str = ""
    tenant_id: str = ""
    session_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        return cls(
            evidence_id=str(data.get("evidence_id") or ""),
            chunk_id=str(data.get("chunk_id") or ""),
            parent_chunk_id=str(data.get("parent_chunk_id") or ""),
            quote=str(data.get("quote") or ""),
            source_title=str(data.get("source_title") or ""),
            url=str(data.get("url") or ""),
            page=data.get("page"),
            published_at=str(data.get("published_at") or ""),
            source_quality=str(data.get("source_quality") or ""),
            supports=as_str_list(data.get("supports")),
            relevance=_safe_relevance(data.get("relevance")),
            document_id=str(data.get("document_id") or ""),
            tenant_id=str(data.get("tenant_id") or ""),
            session_id=data.get("session_id"),
        )


@dataclass
class ClaimItem:
    claim_id: str
    section_id: str
    statement: str
    claim_type: str = "fact"
    evidence_ids: list[str] = field(default_factory=list)
    requires_citation: bool = True
    contains_number: bool = False
    contains_date: bool = False
    confidence: str = "medium"
    caveat: str = ""
    single_source: bool = False
    rejected: bool = False
    reject_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimItem":
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            section_id=str(data.get("section_id") or ""),
            statement=str(data.get("statement") or ""),
            claim_type=str(data.get("claim_type") or "fact"),
            evidence_ids=as_str_list(data.get("evidence_ids")),
            requires_citation=bool(data.get("requires_citation", True)),
            contains_number=bool(data.get("contains_number", False)),
            contains_date=bool(data.get("contains_date", False)),
            confidence=str(data.get("confidence") or "medium"),
            caveat=str(data.get("caveat") or ""),
            single_source=bool(data.get("single_source", False)),
            rejected=bool(data.get("rejected", False)),
            reject_reason=str(data.get("reject_reason") or ""),
        )


@dataclass
class AuditResult:
    citation_coverage: float = 0.0
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: list[str] = field(default_factory=list)
    single_source_numeric_claims: list[str] = field(default_factory=list)
    cross_scope_violations: int = 0
    citation_audit_failed: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrustOutcome:
    """Final delivery decision for the worker (before/at single persist)."""

    report: str
    report_trust: ReportTrust
    legacy_fallback: bool = False
    citation_unverified: bool = False
    citation_audit_failed: bool = False
    audit: Optional[AuditResult] = None
    trusted_pipeline: dict[str, Any] = field(default_factory=dict)
    trusted_shadow: Optional[dict[str, Any]] = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    researcher: Any = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    should_fail_job: bool = False

    def result_metadata(self) -> dict[str, Any]:
        return {
            "report_trust": self.report_trust,
            "legacy_fallback": self.legacy_fallback,
            "citation_unverified": self.citation_unverified,
            "citation_audit_failed": self.citation_audit_failed,
            "trusted_pipeline": self.trusted_pipeline,
            "trusted_shadow": self.trusted_shadow,
            "audit": self.audit.to_dict() if self.audit else None,
        }


class CitationAuditFailed(Exception):
    """Raised when programmatic citation audit fails (permanent for trusted path)."""

    code = "citation_audit_failed"

    def __init__(
        self,
        message: str = "citation audit failed",
        *,
        audit: Optional[AuditResult] = None,
        report: str = "",
        artifacts: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.audit = audit
        self.report = report or ""
        self.artifacts = artifacts or {}
