"""Global Planner — outline only, no unverified facts."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from trusted_report.document_map import document_map_for_planner
from trusted_report.flags import env_int
from trusted_report.llm import call_llm_json
from trusted_report.models import DocumentMapEntry, ReportOutline
from trusted_report import prompts

logger = logging.getLogger(__name__)


def planner_input_payload(
    *,
    question: str,
    report_type: str,
    writing_requirements: str,
    document_map: list[DocumentMapEntry],
    session_summary: str = "",
) -> dict[str, Any]:
    """Build planner inputs; exposes what the model will see (for tests)."""
    budget = env_int("TRUSTED_PLANNER_TOKEN_BUDGET", 2500, minimum=200)
    return {
        "question": question,
        "report_type": report_type,
        "writing_requirements": writing_requirements,
        "document_map": document_map_for_planner(document_map),
        "session_summary": (session_summary or "")[:800],
        "token_budget": budget,
        # Explicit: never attach child full texts
        "includes_child_full_text": False,
    }


async def run_global_planner(
    *,
    question: str,
    report_type: str = "research_report",
    writing_requirements: str = "",
    document_map: list[DocumentMapEntry],
    session_summary: str = "",
    llm_call: Optional[Callable[..., Any]] = None,
) -> ReportOutline:
    payload = planner_input_payload(
        question=question,
        report_type=report_type,
        writing_requirements=writing_requirements,
        document_map=document_map,
        session_summary=session_summary,
    )
    prompt_kwargs = {
        "question": payload["question"],
        "report_type": payload["report_type"],
        "writing_requirements": payload["writing_requirements"],
        "document_map": payload["document_map"],
        "session_summary": payload["session_summary"],
        "token_budget": payload["token_budget"],
    }
    last_err: Optional[Exception] = None
    for _ in range(2):
        try:
            data = await call_llm_json(
                system=prompts.planner_system(),
                user=prompts.planner_user(**prompt_kwargs),
                llm_call=llm_call,
            )
            outline = ReportOutline.from_dict(data)
            if not outline.sections:
                raise ValueError("planner returned no sections")
            return outline
        except Exception as exc:
            last_err = exc
            logger.warning("Planner parse/retry: %s", exc)
    raise RuntimeError(f"Global planner failed: {last_err}")
