"""Research gather only — never calls write_report / DetailedReport drafting."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def gather_research_only(
    *,
    task: str,
    report_type: str = "research_report",
    report_source: str = "web",
    source_urls: Optional[list] = None,
    document_urls: Optional[list] = None,
    tone: Any = None,
    websocket: Any = None,
    headers: Optional[dict] = None,
    query_domains: Optional[list] = None,
    config_path: str = "",
    mcp_enabled: bool = False,
    mcp_strategy: str = "fast",
    mcp_configs: Optional[list] = None,
    max_search_results: Optional[int] = None,
    total_words: Optional[int] = None,
    report_language: Optional[str] = None,
    documents: Optional[list] = None,
) -> tuple[Any, list[dict[str, Any]]]:
    """
    Run GPTResearcher.conduct_research only.

    Returns (gpt_researcher, sources). Does NOT call write_report.
    """
    from gpt_researcher import GPTResearcher
    from gpt_researcher.utils.enum import Tone

    if tone is None:
        tone = Tone.Objective

    params: dict[str, Any] = {
        "query": task,
        "query_domains": query_domains or [],
        "report_type": report_type,
        "report_source": report_source,
        "source_urls": source_urls,
        "document_urls": document_urls,
        "tone": tone,
        "config_path": config_path or "default",
        "websocket": websocket,
        "headers": headers or {},
        "documents": documents,
    }
    if mcp_enabled and mcp_configs:
        params["mcp_configs"] = mcp_configs
        params["mcp_strategy"] = mcp_strategy

    researcher = GPTResearcher(**params)
    if max_search_results is not None:
        researcher.cfg.max_search_results_per_query = int(max_search_results)
    if total_words is not None:
        researcher.cfg.total_words = int(total_words)
    if report_language is not None:
        researcher.cfg.report_language = str(report_language).lower()

    await researcher.conduct_research()
    sources: list[dict[str, Any]] = []
    try:
        sources = list(researcher.get_research_sources() or [])
    except Exception:
        sources = []
    return researcher, sources


async def legacy_write_from_researcher(researcher: Any) -> str:
    """Produce a legacy report body from an already-researched agent (one write)."""
    if researcher is None:
        raise RuntimeError("legacy_write_from_researcher requires researcher")
    report = await researcher.write_report()
    return report if isinstance(report, str) else str(report)
