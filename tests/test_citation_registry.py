import pytest

from gpt_researcher.actions.citation_registry import (
    SourceRegistry,
    extract_domain,
    extract_snippet,
)
from gpt_researcher.actions.markdown_processing import (
    add_numbered_references,
    strip_existing_references_section,
)


def test_extract_domain():
    assert extract_domain("https://www.arxiv.org/abs/123") == "arxiv.org"
    assert extract_domain("https://nature.com/articles/abc") == "nature.com"


def test_extract_snippet_strips_html_and_truncates():
    raw = "<p>Hello <b>world</b> " + ("x" * 400) + "</p>"
    snippet = extract_snippet(raw, max_len=50)
    assert snippet.startswith("「")
    assert snippet.endswith("...」")
    assert "Hello world" in snippet


def test_source_registry_deduplicates_urls():
    registry = SourceRegistry.from_research_sources(
        [
            {"url": "https://a.test/1", "title": "A", "raw_content": "alpha"},
            {"url": "https://a.test/1", "title": "Dup", "raw_content": "ignored"},
            {"url": "https://b.test/2", "title": "B", "raw_content": "beta"},
        ],
        fallback_urls=["https://a.test/1", "https://c.test/3"],
    )

    assert len(registry.entries) == 3
    assert registry.entries[0]["url"] == "https://a.test/1"
    assert registry.entries[2]["url"] == "https://c.test/3"


def test_build_numbered_context_includes_ids():
    registry = SourceRegistry.from_research_sources(
        [{"url": "https://a.test", "title": "Title A", "raw_content": "Body A"}]
    )
    context = registry.build_numbered_context()
    assert "[1] Title: Title A" in context
    assert "URL: https://a.test" in context
    assert "Content: Body A" in context


def test_format_reference_list_contains_required_fields():
    registry = SourceRegistry.from_research_sources(
        [
            {
                "url": "https://arxiv.org/abs/1706.03762",
                "title": "Attention Is All You Need",
                "raw_content": "The dominant sequence transduction models",
            }
        ]
    )
    refs = registry.format_reference_list()

    assert refs.startswith("## 参考文献")
    assert "**[1]** arxiv.org" in refs
    assert "URL: https://arxiv.org/abs/1706.03762" in refs
    assert "原文片段：" in refs
    assert 'id="ref-1"' in refs


def test_strip_existing_references_section():
    report = "# Report\n\nSome claim [1].\n\n## 参考文献\n\n[1] old entry"
    cleaned = strip_existing_references_section(report)
    assert "## 参考文献" not in cleaned
    assert "Some claim [1]." in cleaned


def test_strip_existing_references_section_english_heading():
    report = "# Report\n\nBody.\n\n## References\n\n- https://example.com"
    cleaned = strip_existing_references_section(report)
    assert "## References" not in cleaned
    assert "Body." in cleaned


def test_strip_apa_inline_citations():
    from gpt_researcher.actions.markdown_processing import strip_apa_inline_citations

    report = "Paragraph one.\n\nSource: (Formlabs, n.d.)\n\nParagraph two."
    cleaned = strip_apa_inline_citations(report)
    assert "Source:" not in cleaned
    assert "Paragraph one." in cleaned
    assert "Paragraph two." in cleaned


def test_format_reference_list_english_heading():
    registry = SourceRegistry.from_research_sources(
        [
            {
                "url": "https://arxiv.org/abs/1706.03762",
                "title": "Attention Is All You Need",
                "raw_content": "The dominant sequence transduction models",
            }
        ]
    )
    refs = registry.format_reference_list("## References")

    assert refs.startswith("## References")
    assert "Excerpt:" in refs
    assert "原文片段" not in refs


def test_format_reference_list_omits_unavailable_snippet():
    registry = SourceRegistry.from_research_sources(
        [{"url": "https://blocked.example/page", "title": "", "raw_content": ""}],
        fallback_urls=["https://only-url.example/x"],
    )
    refs = registry.format_reference_list()

    assert "URL: https://blocked.example/page" in refs
    assert "URL: https://only-url.example/x" in refs
    assert "原文片段" not in refs
    assert "原文不可用" not in refs
    assert "Excerpt:" not in refs


def test_normalize_numbered_report_english_heading():
    from gpt_researcher.actions.markdown_processing import normalize_numbered_report

    registry = SourceRegistry.from_research_sources(
        [{"url": "https://example.com", "title": "Example", "raw_content": "Sample text"}]
    )
    raw = "# Title\n\nBody text.\n\n## References\n\n- item"
    result = normalize_numbered_report(raw, registry, references_heading="## References")
    assert "## References" in result
    assert "## 参考文献" not in result


def test_normalize_numbered_report_appends_references():
    from gpt_researcher.actions.markdown_processing import normalize_numbered_report

    registry = SourceRegistry.from_research_sources(
        [{"url": "https://example.com", "title": "Example", "raw_content": "Sample text"}]
    )
    raw = "# Title\n\nBody text.\n\nSource: (Author, n.d.)\n\n## References\n\n- item"
    result = normalize_numbered_report(raw, registry)
    assert "## 参考文献" in result
    assert "example.com" in result
    assert "Source:" not in result
    assert "## References" not in result

    registry = SourceRegistry.from_research_sources(
        [{"url": "https://example.com", "title": "Example", "raw_content": "Sample text"}]
    )
    report = add_numbered_references("# Title\n\nParagraph [1].", registry)
    assert report.startswith("# Title")
    assert "## 参考文献" in report
    assert "example.com" in report
