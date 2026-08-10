"""Independent prompts for each trusted-report stage (do not merge)."""

from __future__ import annotations

import json
from typing import Any


def planner_system() -> str:
    return (
        "You are the Global Planner for a trusted research report pipeline. "
        "You design the report blueprint only: thesis, scope, section structure, "
        "questions each section must answer, and search queries. "
        "Do NOT invent unsupported facts, statistics, URLs, page numbers, or citations. "
        "Output strict JSON only matching the schema."
    )


def planner_user(
    *,
    question: str,
    report_type: str,
    writing_requirements: str,
    document_map: list[dict[str, Any]],
    session_summary: str,
    token_budget: int,
) -> str:
    return (
        f"User question:\n{question}\n\n"
        f"Report type: {report_type}\n"
        f"Writing requirements: {writing_requirements or 'none'}\n"
        f"Token budget for this planning context: {token_budget}\n\n"
        f"Session summary:\n{session_summary or 'none'}\n\n"
        f"Document map (Parent-level only; NOT full text):\n"
        f"{json.dumps(document_map, ensure_ascii=False)[:token_budget * 3]}\n\n"
        "Return JSON with keys: report_thesis, scope, time_range, sections "
        "(section_id, title, purpose, questions_to_answer, depends_on_sections, "
        "search_queries, expected_claim_types), cross_section_questions."
    )


def evidence_system() -> str:
    return (
        "You are the Evidence Extractor. From the provided Child chunk passages only, "
        "extract precise quotable evidence. "
        "quote MUST be a contiguous excerpt from the given chunk text. "
        "Do not paraphrase into a vague summary. "
        "Do not invent chunk_id, URL, page, or numbers absent from the text. "
        "If evidence is insufficient, return {\"evidence\": []}. "
        "Output strict JSON only."
    )


def evidence_user(*, section_id: str, questions: list[str], passages: list[dict[str, Any]]) -> str:
    return (
        f"Section: {section_id}\n"
        f"Questions to answer:\n{json.dumps(questions, ensure_ascii=False)}\n\n"
        f"Candidate Child passages (verbatim):\n"
        f"{json.dumps(passages, ensure_ascii=False)}\n\n"
        "Return JSON: {\"evidence\":[{\"evidence_id\",\"chunk_id\",\"parent_chunk_id\","
        "\"quote\",\"source_title\",\"url\",\"page\",\"published_at\",\"source_quality\","
        "\"supports\",\"relevance\"}]}. "
        "relevance MUST be a number between 0.0 and 1.0 (not Chinese labels)."
    )


def claim_system() -> str:
    return (
        "You are the Claim Builder. Produce minimal auditable claims for the report section. "
        "Each claim MUST list evidence_ids that support it. "
        "Do not invent facts without evidence. "
        "If only weak or conflicting evidence exists, use claim_type=uncertainty. "
        "Output strict JSON only."
    )


def claim_user(
    *,
    section_id: str,
    purpose: str,
    questions: list[str],
    evidence: list[dict[str, Any]],
    expected_types: list[str],
) -> str:
    return (
        f"Section: {section_id}\nPurpose: {purpose}\n"
        f"Questions: {json.dumps(questions, ensure_ascii=False)}\n"
        f"Expected claim types: {expected_types}\n\n"
        f"Evidence JSON:\n{json.dumps(evidence, ensure_ascii=False)}\n\n"
        "Return JSON: {\"claims\":[{\"claim_id\",\"section_id\",\"statement\",\"claim_type\","
        "\"evidence_ids\",\"requires_citation\",\"contains_number\",\"contains_date\","
        "\"confidence\",\"caveat\"}]}"
    )


def writer_system() -> str:
    return (
        "You are the Section Writer. Write prose ONLY from the provided verified claims. "
        "Do not retrieve new facts. Do not invent statistics, URLs, pages, or citation numbers. "
        "After each factual sentence, place a machine marker like [[claim:cl_xxx]] "
        "using the provided claim_id. Do not invent claim ids. "
        "Do not emit [1]-style citation numbers."
    )


def writer_user(
    *,
    section: dict[str, Any],
    claims: list[dict[str, Any]],
    prior_claims: list[dict[str, Any]],
    parent_context: str,
    word_budget: int,
) -> str:
    return (
        f"Section blueprint:\n{json.dumps(section, ensure_ascii=False)}\n\n"
        f"Verified claims for this section:\n{json.dumps(claims, ensure_ascii=False)}\n\n"
        f"Prior verified claims (context only):\n{json.dumps(prior_claims, ensure_ascii=False)}\n\n"
        f"Parent context (non-citeable background):\n{parent_context or 'none'}\n\n"
        f"Word budget: ~{word_budget}\n"
        "Write the section markdown body with [[claim:...]] markers."
    )


def synthesis_system() -> str:
    return (
        "You are the Synthesis Editor. Improve global narrative: order, transitions, "
        "comparisons, contradiction handling, and conclusion hierarchy. "
        "You MUST preserve every [[claim:...]] marker (or remap consistently). "
        "Do not add external facts without a claim marker. "
        "For contradictions: explain with existing claims, mark unresolved, or soften language."
    )


def synthesis_user(
    *,
    outline: dict[str, Any],
    section_bodies: dict[str, str],
    claims_brief: list[dict[str, Any]],
    cross_questions: list[str],
    token_budget: int,
) -> str:
    return (
        f"Global outline:\n{json.dumps(outline, ensure_ascii=False)}\n\n"
        f"Section drafts:\n{json.dumps(section_bodies, ensure_ascii=False)}\n\n"
        f"Verified claims brief:\n{json.dumps(claims_brief, ensure_ascii=False)}\n\n"
        f"Cross-section questions:\n{json.dumps(cross_questions, ensure_ascii=False)}\n\n"
        f"Token budget: {token_budget}\n"
        "Return the full synthesized markdown report body, preserving [[claim:...]] markers."
    )
