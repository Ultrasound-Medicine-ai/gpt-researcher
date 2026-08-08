"""Unit tests for deterministic citation inject (quality-safe)."""

from gpt_researcher.actions.citation_registry import SourceRegistry
from gpt_researcher.actions.deterministic_cite import inject_deterministic_citations


def test_inject_returns_unchanged_without_embeddings_and_empty_registry():
    report = "# Hello\n\nNo sources here."
    assert inject_deterministic_citations(report, None) == report
    empty = SourceRegistry([])
    assert inject_deterministic_citations(report, empty) == report


class _FakeEmbeddings:
    def embed_documents(self, texts):
        # Distinct one-hot-ish vectors by first char code
        vecs = []
        for t in texts:
            v = [0.0] * 8
            if not t:
                vecs.append(v)
                continue
            v[ord(t[0]) % 8] = 1.0
            if "alpha" in t.lower() or "主张" in t:
                v[0] = 1.0
            if "beta" in t.lower() or "另一" in t:
                v[1] = 1.0
            vecs.append(v)
        return vecs

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def test_inject_adds_citations_and_renumbers():
    registry = SourceRegistry.from_research_sources(
        [
            {"url": "https://a.test", "title": "A", "raw_content": "alpha evidence about topic"},
            {"url": "https://b.test", "title": "B", "raw_content": "beta evidence other angle"},
        ]
    )
    report = "主张与 alpha evidence about topic 相关。另一点涉及 beta evidence other angle。\n\n## 参考文献\nold"
    out = inject_deterministic_citations(
        report, registry, embeddings=_FakeEmbeddings(), threshold=0.1
    )
    assert "## 参考文献" in out
    assert "[1]" in out
    # Should not crash and should keep body content
    assert "alpha" in out.lower() or "主张" in out
