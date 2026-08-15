# Candidate Quality Check V2

> 旧版 candidate-021 至 candidate-080 已作为 failed draft 保留，不参与本次检查或任何指标。
> V2 仅复用已人工审核的 Frozen Pilot 正文证据；未读取或使用旧草稿的脏 Evidence。

| Check | Result |
| --- | ---: |
| exact_duplicate_query | 0 |
| normalized_duplicate_query | 0 |
| max_same_12_char_prefix | 1 |
| banned_template_hits | 0 |
| source_title_leakage | 0 |
| ingestion_prompt_leakage | 0 |
| noisy_supporting_excerpt | 0 |
| blocked_topic_evidence_mismatch | 0 |
| cross_parent_or_child_violation | 0 |
| multi_parent_violation | 0 |
| postgresql_child_parent_validation | 0 |
| postgresql_cross_child_index_gap | 0 |

- 新 Candidate：60；Unique Query：60。
- 类型分布：{'exact_keyword': 15, 'semantic_paraphrase': 15, 'cross_chunk_boundary': 15, 'multi_parent_synthesis': 15}。
- topic_group 分布：{'sse': 9, 'hpa_vpa': 12, 'redis_lock': 6, 'cache_patterns': 6, 'fastapi': 6, 'redis_hot_key': 6, 'redis_architecture': 6, 'network_performance': 6, 'cache_consistency': 3}。
- Proposed split：{'holdout': 28, 'main': 52}；同一 topic_group 在全文件中保持单一 split。
- 证据污染丢弃数：0（V2 候选池限定为 Frozen Pilot 已审核正文；旧版 60 条草稿不计入 V2 候选池）。
