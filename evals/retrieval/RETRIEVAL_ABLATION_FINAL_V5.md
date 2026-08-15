# Retrieval Ablation - Final 40 Gold V5

- Frozen Gold: `final_v1`, 40 human-reviewed cases.
- FTS uses jieba-segmented text stored in `content_tsv` and keyword-level OR tsquery.
- Raw metrics use original Child rankings; Evidence Recall@3500 uses final packed Context only.

## FTS health

- FTS non-empty rate: 1.0000
- FTS Top20 Gold hit rate: 0.8750

## Aggregate metrics

| Scheme | Hit@5 | Hit@8 | Recall@5 | Recall@8 | MRR@8 | Parent Recall@8 | Evidence Recall@3500 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. FTS only | 0.7750 | 0.8000 | 0.6092 | 0.6675 | 0.5550 | 0.7425 | N/A |
| B. pgvector only | 0.8000 | 0.9000 | 0.5925 | 0.7517 | 0.5983 | 0.8475 | N/A |
| C. FTS + pgvector + calibrated RRF | 0.8250 | 0.9250 | 0.6175 | 0.7592 | 0.6136 | 0.8175 | N/A |
| D. Calibrated Hybrid + Context | 0.8250 | 0.9250 | 0.6175 | 0.7592 | 0.6136 | 0.8175 | 0.6204 |

## Recall@8 by query type

| Scheme | exact_keyword | semantic_paraphrase | cross_chunk_boundary | multi_parent_synthesis |
|---|---:|---:|---:|---:|
| A. FTS only | 1.0000 | 0.6500 | 0.5500 | 0.4700 |
| B. pgvector only | 0.8000 | 0.8000 | 0.7667 | 0.6400 |
| C. FTS + pgvector + calibrated RRF | 0.9000 | 0.9000 | 0.6667 | 0.5700 |
| D. Calibrated Hybrid + Context | 0.9000 | 0.9000 | 0.6667 | 0.5700 |

## Three-case sanity

- candidate-021: non-empty=True, gold_ranks={'a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911': 1}
- candidate-026: non-empty=True, gold_ranks={'c8bb7bc9-148d-484b-8640-2c75872ffc94': 4}
- candidate-031: non-empty=True, gold_ranks={'da6f4372-fa23-4d84-b2f3-98dd256253f0': None, 'b39ddde1-9b8a-46d1-bcfc-23c468c1634f': None}
