"""Cheap harness scorer unit tests (no live research)."""

from evals.harness_eval.scorers.citations import score_citations
from evals.harness_eval.scorers.language import score_report_language, chinese_char_ratio
from evals.harness_eval.scorers.retrieval import score_must_mention


def test_chinese_ratio_detects_cjk():
    assert chinese_char_ratio("你好世界 hello") > 0.4
    assert chinese_char_ratio("hello world") == 0.0


def test_score_report_language_zh():
    report = "# 报告\n\n这是中文内容。\n\n## 参考文献\n"
    ok, fails = score_report_language(
        report, {"lang": "zh", "refs_heading": "## 参考文献", "min_chinese_ratio": 0.2}
    )
    assert ok, fails


def test_score_citations_dangling():
    report = "Claim [1] and [9].\n\n## 参考文献\n\n**[1]** a.test\n"
    ok, fails = score_citations(
        report, {"min_bracket_cites": 1, "cites_subseteq_sources": True}, source_count=1
    )
    assert not ok
    assert any("dangling" in f or "invalid" in f for f in fails)


def test_score_must_mention():
    ok, fails, hits = score_must_mention("hello UNIQUE_TOKEN world", ["UNIQUE_TOKEN"])
    assert ok
    assert hits["UNIQUE_TOKEN"] is True
