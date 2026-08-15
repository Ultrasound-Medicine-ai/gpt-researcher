# Retrieval Ablation — Final 40 Gold

- Gold: 40 human-reviewed frozen cases (`final_v1`).
- Raw metrics use original Child rankings; Evidence Recall@3500 uses only the final context scheme after Parent Diversity, Neighbor Expansion, Dedup, and budget packing.

## Aggregate metrics

| Scheme | Hit@5 | Hit@8 | Recall@5 | Recall@8 | MRR@8 | Parent Recall@8 | Evidence Recall@3500 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. FTS only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | N/A |
| B. pgvector only | 0.8000 | 0.9000 | 0.5925 | 0.7517 | 0.5983 | 0.8475 | N/A |
| C. FTS + pgvector + RRF | 0.8000 | 0.9000 | 0.5925 | 0.7517 | 0.5983 | 0.8475 | N/A |
| D. Hybrid RRF + context | 0.8000 | 0.9000 | 0.5925 | 0.7517 | 0.5983 | 0.8475 | 0.6183 |

## Recall@8 by query type

| Scheme | exact_keyword | semantic_paraphrase | cross_chunk_boundary | multi_parent_synthesis |
|---|---:|---:|---:|---:|
| A. FTS only | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| B. pgvector only | 0.8000 | 0.8000 | 0.7667 | 0.6400 |
| C. FTS + pgvector + RRF | 0.8000 | 0.8000 | 0.7667 | 0.6400 |
| D. Hybrid RRF + context | 0.8000 | 0.8000 | 0.7667 | 0.6400 |

- D mean `context_token_count_estimated`: 3028.95
- Vector non-empty cases: 40/40
- Context errors: 0
