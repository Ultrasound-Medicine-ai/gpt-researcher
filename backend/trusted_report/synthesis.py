"""Synthesis Editor — global narrative without adding unsupported facts."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

from trusted_report.flags import env_int
from trusted_report.models import ClaimItem, ReportOutline
from trusted_report.writer import CLAIM_MARKER_RE, extract_claim_markers
from trusted_report import prompts

logger = logging.getLogger(__name__)


def preserve_claim_markers(original: str, synthesized: str) -> str:
    """
    Ensure all original claim markers still appear; append missing ones.
    """
    needed = set(extract_claim_markers(original))
    have = set(extract_claim_markers(synthesized))
    missing = needed - have
    body = (synthesized or "").strip() or (original or "").strip()
    if not missing:
        return body
    # Append missing markers from original sentences when possible
    extras = []
    for mid in sorted(missing):
        m = re.search(rf"([^\n]*\[\[claim:{re.escape(mid)}\]\])", original or "")
        extras.append(m.group(1) if m else f"[[claim:{mid}]]")
    return (body + "\n\n" + "\n\n".join(extras)).strip()


def join_section_drafts(section_bodies: dict[str, str], outline: ReportOutline) -> str:
    parts = []
    for sec in outline.sections:
        body = (section_bodies.get(sec.section_id) or "").strip()
        if body:
            parts.append(body)
    # include any extras
    for sid, body in section_bodies.items():
        if sid not in {s.section_id for s in outline.sections} and body.strip():
            parts.append(body.strip())
    return "\n\n".join(parts).strip()


async def synthesize_report(
    outline: ReportOutline,
    section_bodies: dict[str, str],
    claims: list[ClaimItem],
    *,
    llm_call: Optional[Callable[..., Any]] = None,
) -> str:
    original = join_section_drafts(section_bodies, outline)
    if not original:
        return ""

    brief = [
        {
            "claim_id": c.claim_id,
            "section_id": c.section_id,
            "statement": c.statement,
            "claim_type": c.claim_type,
        }
        for c in claims
        if not c.rejected
    ][:80]

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
                await rt.register_llm_call("trusted_synthesis")
        except Exception:
            pass
        return await create_chat_completion(
            messages=messages,
            model=cfg.smart_llm_model,
            llm_provider=cfg.smart_llm_provider,
            temperature=0.3,
            llm_kwargs=cfg.llm_kwargs,
        )

    budget = env_int("TRUSTED_SYNTHESIS_TOKEN_BUDGET", 4000, minimum=500)
    try:
        raw = await _call(
            [
                {"role": "system", "content": prompts.synthesis_system()},
                {
                    "role": "user",
                    "content": prompts.synthesis_user(
                        outline=outline.to_dict(),
                        section_bodies=section_bodies,
                        claims_brief=brief,
                        cross_questions=outline.cross_section_questions,
                        token_budget=budget,
                    ),
                },
            ]
        )
        text = raw if isinstance(raw, str) else str(raw)
        text = re.sub(r"\[(\d{1,3})\]", "", text)
        return preserve_claim_markers(original, text)
    except Exception as exc:
        logger.warning("Synthesis failed — using joined drafts: %s", exc)
        return original
