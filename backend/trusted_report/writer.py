"""Section Writer — prose from verified claims with [[claim:id]] markers."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

from trusted_report.flags import env_int
from trusted_report.llm import call_llm_json
from trusted_report.models import ClaimItem, OutlineSection
from trusted_report import prompts

logger = logging.getLogger(__name__)

CLAIM_MARKER_RE = re.compile(r"\[\[claim:([^\]]+)\]\]")


def extract_claim_markers(text: str) -> list[str]:
    return CLAIM_MARKER_RE.findall(text or "")


def ensure_claim_markers(text: str, claims: list[ClaimItem]) -> str:
    """If model omitted markers, append statements with markers (deterministic fallback)."""
    body = (text or "").strip()
    present = set(extract_claim_markers(body))
    missing = [c for c in claims if c.claim_id not in present and not c.rejected]
    if not missing:
        return body
    lines = [body] if body else []
    for c in missing:
        lines.append(f"{c.statement} [[claim:{c.claim_id}]]")
    return "\n\n".join(lines).strip()


def flag_unmarked_numeric_sentences(text: str, claims: list[ClaimItem]) -> list[str]:
    """Warn on sentences with digits that lack a claim marker nearby."""
    warnings: list[str] = []
    claim_ids = {c.claim_id for c in claims}
    for sentence in re.split(r"(?<=[。.!?\n])\s*", text or ""):
        s = sentence.strip()
        if not s:
            continue
        if not re.search(r"\d", s):
            continue
        markers = extract_claim_markers(s)
        if not markers:
            warnings.append(f"unmarked_numeric_sentence:{s[:80]}")
        elif any(m not in claim_ids for m in markers):
            warnings.append(f"unknown_claim_marker:{markers}")
    return warnings


def assert_writer_inputs_are_verified(
    claims: list[ClaimItem],
    *,
    legacy_report_body: Optional[str] = None,
) -> list[ClaimItem]:
    """
    Authenticity gate: Writer may only see programmatically accepted claims.
    Never pass a legacy report body into the writer path.
    """
    if legacy_report_body:
        raise ValueError("Section Writer must not receive legacy report body")
    accepted: list[ClaimItem] = []
    for c in claims:
        if c.rejected:
            continue
        if c.requires_citation and not c.evidence_ids and c.claim_type != "uncertainty":
            continue
        accepted.append(c)
    return accepted


async def write_section(
    section: OutlineSection,
    claims: list[ClaimItem],
    *,
    prior_claims: Optional[list[ClaimItem]] = None,
    parent_context: str = "",
    evidence: Optional[list] = None,
    legacy_report_body: Optional[str] = None,
    llm_call: Optional[Callable[..., Any]] = None,
) -> tuple[str, list[str]]:
    accepted = assert_writer_inputs_are_verified(
        claims, legacy_report_body=legacy_report_body
    )
    if not accepted:
        return "", ["no_claims_for_section"]
    # Evidence is for citation binding context only (ids), not free-form legacy prose
    evidence_ids = {
        getattr(e, "evidence_id", None) or (e.get("evidence_id") if isinstance(e, dict) else None)
        for e in (evidence or [])
    }
    evidence_ids.discard(None)
    for c in accepted:
        if c.requires_citation and c.evidence_ids:
            if evidence_ids and not any(eid in evidence_ids for eid in c.evidence_ids):
                return "", [f"claim_evidence_not_in_section:{c.claim_id}"]

    # Prefer text response; if JSON wrapper, unwrap
    async def _call(messages):
        if llm_call is not None:
            return await llm_call(messages)
        from gpt_researcher.utils.llm import create_chat_completion
        from gpt_researcher.config.config import Config

        cfg = Config()
        try:
            from jobs.runtime import JobRuntime

            rt = JobRuntime.current()
            if rt is not None:
                await rt.register_llm_call("trusted_section_writer")
        except Exception:
            pass
        return await create_chat_completion(
            messages=messages,
            model=cfg.smart_llm_model,
            llm_provider=cfg.smart_llm_provider,
            temperature=0.3,
            llm_kwargs=cfg.llm_kwargs,
        )

    word_budget = env_int("TRUSTED_SECTION_WORD_BUDGET", 400, minimum=80)
    user = prompts.writer_user(
        section={
            "section_id": section.section_id,
            "title": section.title,
            "purpose": section.purpose,
            "questions_to_answer": section.questions_to_answer,
        },
        claims=[c.to_dict() for c in accepted],
        prior_claims=[c.to_dict() for c in (prior_claims or [])][:12],
        parent_context=parent_context[:1200],
        word_budget=word_budget,
    )
    try:
        raw = await _call(
            [
                {"role": "system", "content": prompts.writer_system()},
                {"role": "user", "content": user},
            ]
        )
        text = raw if isinstance(raw, str) else str(raw)
        # Some models wrap JSON {"body": "..."}
        if text.strip().startswith("{"):
            try:
                from trusted_report.llm import extract_json_object

                data = extract_json_object(text)
                text = str(data.get("body") or data.get("markdown") or text)
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Section writer failed, using claim fallback: %s", exc)
        text = ""

    text = ensure_claim_markers(text, accepted)
    # Strip forged [n] numbers from model
    text = re.sub(r"\[(\d{1,3})\]", "", text)
    warnings = flag_unmarked_numeric_sentences(text, accepted)
    heading = f"## {section.title}\n\n"
    if not text.lstrip().startswith("#"):
        text = heading + text
    return text, warnings
