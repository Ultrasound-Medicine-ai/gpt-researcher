"""Verification tests for report language decoupling."""

from types import SimpleNamespace

from gpt_researcher.actions.report_generation import get_effective_report_language
from gpt_researcher.actions.citation_registry import references_heading_for_language
from gpt_researcher.prompts import PromptFamily


def test_effective_report_language_user_override():
    cfg = SimpleNamespace(report_language="english", language="chinese")
    assert get_effective_report_language(cfg) == "english"


def test_effective_report_language_falls_back_to_language():
    cfg = SimpleNamespace(language="chinese")
    assert get_effective_report_language(cfg) == "chinese"


def test_effective_report_language_default_chinese():
    cfg = SimpleNamespace()
    assert get_effective_report_language(cfg) == "chinese"


def test_no_auto_chinese_from_query():
    """Ensure old query-based override is removed."""
    import gpt_researcher.actions.report_generation as rg

    assert not hasattr(rg, "_resolve_report_language")


def test_references_heading_by_language():
    assert references_heading_for_language("chinese") == "## 参考文献"
    assert references_heading_for_language("english") == "## References"


def test_report_prompt_uses_language_not_query_language():
    prompt = PromptFamily.generate_report_prompt(
        question="3D打印在医疗领域的应用",
        context="[1] sample",
        report_source="web",
        language="english",
        citation_style="numbered",
    )
    assert "Write the entire report in english only" in prompt
    assert "same language as the research query" not in prompt
    assert "You MUST write the report in the following language: english" in prompt


def test_search_prompt_bilingual_rules():
    prompt = PromptFamily.generate_search_queries_prompt(
        question="3D打印医疗应用",
        parent_query="",
        report_type="research_report",
        max_iterations=3,
        context=[],
    )
    assert "exactly 3 queries" in prompt
    assert "Chinese queries" in prompt
    assert "English keyword queries" in prompt
    assert "Preserve the research intent" in prompt
