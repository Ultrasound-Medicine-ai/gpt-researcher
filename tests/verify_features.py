"""Static integration verification script (no LLM/API calls)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gpt_researcher.actions.citation_registry import (
    SourceRegistry,
    references_heading_for_language,
)
from gpt_researcher.actions.markdown_processing import normalize_numbered_report
from gpt_researcher.actions.report_generation import get_effective_report_language
from gpt_researcher.config.config import Config
from gpt_researcher.prompts import PromptFamily
from types import SimpleNamespace


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    msg = f"[{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


results: list[bool] = []

# --- Config ---
cfg = Config("default")
results.append(check("CITATION_STYLE default is numbered", getattr(cfg, "citation_style", "") == "numbered"))
results.append(check("REPORT_LANGUAGE config exists", hasattr(cfg, "report_language")))

# --- Numbered citations post-process ---
registry = SourceRegistry.from_research_sources(
    [{"url": "https://example.com/a", "title": "Example A", "raw_content": "content a"}],
    fallback_urls=["https://example.com/b"],
)
raw_apa = "# Title\n\nClaim here.\n\nSource: (Author, n.d.)\n\n## References\n\n- old"
normalized = normalize_numbered_report(
    raw_apa,
    registry,
    references_heading=references_heading_for_language("chinese"),
)
results.append(check("Strip APA Source line", "Source:" not in normalized))
results.append(check("Strip LLM References section", "## References\n\n- old" not in normalized))
results.append(check("Append ## 参考文献", "## 参考文献" in normalized))
results.append(check("Reference URL present", "https://example.com/a" in normalized))
results.append(check("Two sources from registry", normalized.count("**[1]**") >= 1 and normalized.count("**[2]**") >= 1))

english_refs = normalize_numbered_report(
    "# Report\n\nText [1].",
    registry,
    references_heading=references_heading_for_language("english"),
)
results.append(check("English references heading", "## References" in english_refs))
results.append(check("English excerpt label", "Excerpt:" in english_refs))

# --- Report language ---
results.append(check(
    "User report_language overrides cfg.language",
    get_effective_report_language(SimpleNamespace(report_language="english", language="chinese")) == "english",
))
results.append(check(
    "Removed _resolve_report_language",
    not hasattr(__import__("gpt_researcher.actions.report_generation", fromlist=["x"]), "_resolve_report_language"),
))

report_prompt = PromptFamily.generate_report_prompt(
    question="中文主题",
    context="ctx",
    report_source="web",
    language="english",
    citation_style="numbered",
)
results.append(check("Report prompt targets english", "Write the entire report in english only" in report_prompt))
results.append(check("No query-language lock", "same language as the research query" not in report_prompt))
results.append(check("Numbered citation instruction", "[1], [2]" in report_prompt))

search_prompt = PromptFamily.generate_search_queries_prompt(
    question="中文 query",
    parent_query="",
    report_type="research_report",
    max_iterations=3,
)
results.append(check("Search bilingual rules present", "English keyword queries" in search_prompt))
results.append(check("Search query count cap", "exactly 3 queries" in search_prompt))

# --- Backend wiring (AST / text scan) ---
server_utils = (ROOT / "backend" / "server" / "server_utils.py").read_text(encoding="utf-8")
results.append(check("WebSocket extracts report_language", 'json_data.get("report_language")' in server_utils))

basic_report = (ROOT / "backend" / "report_type" / "basic_report" / "basic_report.py").read_text(encoding="utf-8")
results.append(check("BasicReport sets cfg.report_language", "cfg.report_language" in basic_report))

writer = (ROOT / "gpt_researcher" / "skills" / "writer.py").read_text(encoding="utf-8")
results.append(check("Writer sends report_complete", '"type": "report_complete"' in writer))
results.append(check("Writer numbered for research_report/deep", '"research_report", "deep"' in writer))

use_ws = (ROOT / "frontend" / "nextjs" / "hooks" / "useWebSocket.ts").read_text(encoding="utf-8")
results.append(check("Frontend WS sends report_language", "report_language:" in use_ws))
results.append(check("Frontend handles report_complete", "report_complete" in use_ws))

research_results = (ROOT / "frontend" / "nextjs" / "components" / "ResearchResults.tsx").read_text(encoding="utf-8")
results.append(check("Frontend prefers answer for report", "Prefer post-processed answer" in research_results))

chat_py = (ROOT / "backend" / "chat" / "chat.py").read_text(encoding="utf-8")
results.append(check("Chat uses report_language", "report_language=" in chat_py and "Respond in" in chat_py))

page_tsx = (ROOT / "frontend" / "nextjs" / "app" / "page.tsx").read_text(encoding="utf-8")
results.append(check("Chat API passes report_language", "report_language: chatBoxSettings.report_language" in page_tsx))

research_form = (ROOT / "frontend" / "nextjs" / "components" / "Task" / "ResearchForm.tsx").read_text(encoding="utf-8")
results.append(check("ReportLanguageSelector in form", "ReportLanguageSelector" in research_form))

# --- Search lane does NOT use report_language ---
query_processing = (ROOT / "gpt_researcher" / "actions" / "query_processing.py").read_text(encoding="utf-8")
results.append(check("Search lane has no report_language", "report_language" not in query_processing))

passed = sum(results)
total = len(results)
print(f"\nSummary: {passed}/{total} checks passed")
sys.exit(0 if passed == total else 1)
