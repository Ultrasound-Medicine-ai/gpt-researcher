# FTS Fusion Experiment

- Gold: frozen `final_v1`; no Gold, Query, retrieval parameter, or production code changes.
- Selection uses Parent-grouped Main only; Holdout is read once for validation.

- Split: Main 30 / Holdout 10
- Selected on Main: `agreement_calibrated_all`

| Variant | Main Recall@8 | Holdout Recall@8 | All Recall@8 | All MRR@8 |
|---|---:|---:|---:|---:|
| pgvector_only | 0.7356 | 0.8000 | 0.7517 | 0.5983 |
| equal_rrf | 0.6622 | 0.9000 | 0.7217 | 0.5800 |
| calibrated_050_all | 0.6956 | 0.9000 | 0.7467 | 0.6302 |
| calibrated_075_all | 0.7122 | 0.9000 | 0.7592 | 0.5907 |
| agreement_calibrated_all | 0.7122 | 0.9000 | 0.7592 | 0.6136 |

- Holdout delta vs PGVector: +0.1000
- Selected Evidence Recall@3500 (all): 0.6204
