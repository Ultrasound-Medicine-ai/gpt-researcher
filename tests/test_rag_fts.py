from rag.fts import fts_anchor_terms, fts_index_text, fts_or_query, fts_terms


def test_chinese_cache_query_becomes_keyword_or_query():
    query = "先删除缓存再更新数据库时，并发读请求为什么仍可能把旧数据重新写入缓存？"
    terms = set(fts_terms(query))
    assert {"缓存", "数据库", "并发", "旧", "数据"}.issubset(terms)
    assert " | " in fts_or_query(query)


def test_mixed_technical_identifiers_are_preserved():
    terms = set(fts_terms("Redis 分布式锁释放时，requestId 校验和 Lua 脚本各负责什么？"))
    assert {"redis", "requestid", "lua"}.issubset(terms)


def test_cross_language_redlock_query_is_not_and_joined():
    query = "设计 Redlock 时，释放锁怎样确认所有者，获取锁又以什么条件判定成功？"
    rendered = fts_or_query(query)
    assert "redlock" in rendered
    assert " & " not in rendered


def test_api_command_tokens_are_preserved():
    terms = set(fts_terms("SET NX PX"))
    assert {"set", "nx", "px"}.issubset(terms)


def test_index_text_preserves_term_frequency_but_query_deduplicates():
    assert fts_index_text("Redis Redis").split() == ["redis", "redis"]
    assert fts_index_text("Redis Redis Redis Redis").split() == [
        "redis", "redis", "redis"
    ]
    assert fts_terms("Redis Redis") == ["redis"]


def test_technical_anchor_detection_is_deterministic():
    assert fts_anchor_terms("Redis SET NX PX with requestId and 3500-token budget") == [
        "set", "nx", "px", "requestid", "3500"
    ]


def test_common_product_word_is_recalled_but_not_treated_as_strong_anchor():
    assert fts_terms("Redis architecture") == ["redis", "architecture"]
    assert fts_anchor_terms("Redis architecture") == []
