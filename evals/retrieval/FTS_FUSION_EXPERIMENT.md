# FTS Fusion Experiment

- Gold: frozen `final_v1`; no Gold, Query, retrieval parameter, or production code changes.
- Selection uses Parent-grouped Main only; Holdout is read once for validation.

- Split: Main 30 / Holdout 10
- Selected on Main: `wrrf_100_gate_cap1`

| Variant | Main Recall@8 | Holdout Recall@8 | All Recall@8 | All MRR@8 |
|---|---:|---:|---:|---:|
| pgvector_only | 0.7356 | 0.8000 | 0.7517 | 0.5983 |
| equal_rrf | 0.6772 | 0.8000 | 0.7079 | 0.5475 |
| wrrf_025_intersection | 0.7244 | 0.8000 | 0.7433 | 0.6027 |
| wrrf_050_intersection | 0.7356 | 0.8000 | 0.7517 | 0.5529 |
| wrrf_025_gate_cap1 | 0.7244 | 0.8000 | 0.7433 | 0.6027 |
| wrrf_050_gate_cap1 | 0.7356 | 0.8000 | 0.7517 | 0.5529 |
| wrrf_100_gate_cap1 | 0.7356 | 0.8000 | 0.7517 | 0.5579 |

- Holdout delta vs PGVector: +0.0000
- Selected Evidence Recall@3500 (all): 0.5733
