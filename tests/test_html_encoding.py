# -*- coding: utf-8 -*-
"""Tests for lightweight HTML decoding (no chardet)."""

from gpt_researcher.actions.citation_registry import extract_snippet, maybe_repair_mojibake
from gpt_researcher.scraper.utils import decode_html_bytes


def test_decode_utf8_when_requests_defaults_latin1():
    original = "知乎，让每一次点击都充满意义"
    content = original.encode("utf-8")
    decoded = decode_html_bytes(
        content,
        declared_encoding="ISO-8859-1",
        content_type="text/html",
    )
    assert decoded == original


def test_decode_respects_content_type_charset():
    original = "你好世界"
    content = original.encode("gb18030")
    decoded = decode_html_bytes(
        content,
        declared_encoding="ISO-8859-1",
        content_type="text/html; charset=gb18030",
    )
    assert decoded == original


def test_decode_reads_meta_charset():
    body = "标题：测试".encode("gb18030")
    html = b'<html><head><meta charset="gb18030"></head><body>' + body + b"</body></html>"
    decoded = decode_html_bytes(html, declared_encoding="ISO-8859-1")
    assert "测试" in decoded


def test_maybe_repair_mojibake_restores_chinese():
    original = "知乎，让每一次点击都充满意义"
    garbled = original.encode("utf-8").decode("latin-1")
    fixed = maybe_repair_mojibake(garbled)
    assert fixed == original


def test_extract_snippet_repairs_mojibake():
    original = "知乎，让每一次点击都充满意义"
    garbled = original.encode("utf-8").decode("latin-1")
    snippet = extract_snippet(garbled)
    assert "知乎" in snippet
    assert "ç" not in snippet
