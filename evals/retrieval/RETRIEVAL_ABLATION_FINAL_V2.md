# Retrieval Ablation — Final 40 Gold V2

- Frozen Gold: `final_v1`, 40 human-reviewed cases.
- FTS uses jieba-segmented text stored in `content_tsv` and keyword-level OR tsquery.
- Raw metrics use original Child rankings; Evidence Recall@3500 uses final packed Context only.

## FTS health

- FTS non-empty rate: 1.0000
- FTS Top20 Gold hit rate: 0.8250

## Aggregate metrics

| Scheme | Hit@5 | Hit@8 | Recall@5 | Recall@8 | MRR@8 | Parent Recall@8 | Evidence Recall@3500 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. FTS only | 0.6500 | 0.7000 | 0.5188 | 0.6125 | 0.4523 | 0.6625 | N/A |
| B. pgvector only | 0.8000 | 0.9000 | 0.5925 | 0.7517 | 0.5983 | 0.8475 | N/A |
| C. FTS + pgvector + RRF | 0.7750 | 0.8500 | 0.6021 | 0.7079 | 0.5475 | 0.7579 | N/A |
| D. Hybrid + Context | 0.7750 | 0.8500 | 0.6021 | 0.7079 | 0.5475 | 0.7579 | 0.5400 |

## Recall@8 by query type

| Scheme | exact_keyword | semantic_paraphrase | cross_chunk_boundary | multi_parent_synthesis |
|---|---:|---:|---:|---:|
| A. FTS only | 0.9000 | 0.6000 | 0.5000 | 0.4500 |
| B. pgvector only | 0.8000 | 0.8000 | 0.7667 | 0.6400 |
| C. FTS + pgvector + RRF | 0.8000 | 0.8667 | 0.6000 | 0.5650 |
| D. Hybrid + Context | 0.8000 | 0.8667 | 0.6000 | 0.5650 |

## Three-case sanity

- candidate-021: non-empty=True, gold_ranks={'a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911': 1}
- candidate-026: non-empty=True, gold_ranks={'c8bb7bc9-148d-484b-8640-2c75872ffc94': 4}
- candidate-031: non-empty=True, gold_ranks={'da6f4372-fa23-4d84-b2f3-98dd256253f0': None, 'b39ddde1-9b8a-46d1-bcfc-23c468c1634f': None}
