# Portfolio evaluation metrics

- Generated (UTC): `2026-08-10T17:07:05.779436+00:00`
- Sample size (SimpleQA requested / hallucination requested): **100**
- Sample seed: **42**
- SimpleQA sample mode: **stratified**

## Pillar ledger (do not merge into one accuracy)

| Pillar | What it measures | Notes |
|--------|------------------|-------|
| A Fact (SimpleQA) | short-form factuality | topic-stratified sample |
| B Faithfulness (hallucination) | MAJOR vs evidence pack | full corpus when n≥70 |
| C Product behavior | dialogue / tool / fuzz / memory | cheap JSONL gates |

## Gate layers

| Layer | Result | Notes |
|-------|--------|-------|
| cheap (offline) | PASS | dialogue/tool/memory + report scorers |
| full harness | PASS | live research sample |
| live chat | PASS | `/api/chat` tool routing |
| SimpleQA | see metrics | factuality of research reports |
| Hallucination | see metrics | faithfulness vs retrieved context |

## Headline numbers (resume-friendly)

### A — Fact (SimpleQA)

- **accuracy (among attempted):** 81.5%
- **F1:** 0.781
- **correct rate:** 75.0% (100 graded)
- **effective_n / mode:** 100 / `stratified`
- **topic strata:** `{'Art': 13, 'Geography': 10, 'History': 4, 'Music': 8, 'Other': 11, 'Politics': 16, 'Science and technology': 20, 'Sports': 8, 'TV shows': 7, 'Video games': 3}`
- **answer_type mix (report-only):** `{'Date': 31, 'Number': 18, 'Other': 25, 'Person': 18, 'Place': 8}`
- **cost:** $5.1063

### B — Faithfulness (hallucination)

- **MAJOR hallucination detection rate:** 65.7% (46/70 evaluated)
- **effective_n:** 70 (requested 70)
- **Judge mode:** `multi_source_evidence_pack_major_only`
- **Severity mix:** MAJOR 46 / MINOR 8 / NONE 16
- **by risk bucket:** `{'fresh_news': {'n': 9, 'evaluated': 9, 'major': 6, 'hallucinated': 6, 'major_rate': 0.6666666666666666, 'hallucination_rate': 0.6666666666666666}, 'howto_technical': {'n': 16, 'evaluated': 16, 'major': 10, 'hallucinated': 10, 'major_rate': 0.625, 'hallucination_rate': 0.625}, 'landscape_vendor': {'n': 6, 'evaluated': 6, 'major': 5, 'hallucinated': 5, 'major_rate': 0.8333333333333334, 'hallucination_rate': 0.8333333333333334}, 'other': {'n': 33, 'evaluated': 33, 'major': 21, 'hallucinated': 21, 'major_rate': 0.6363636363636364, 'hallucination_rate': 0.6363636363636364}, 'pricing_compare': {'n': 6, 'evaluated': 6, 'major': 4, 'hallucinated': 4, 'major_rate': 0.6666666666666666, 'hallucination_rate': 0.6666666666666666}}`
- **cost:** $3.7210

### C — Product behavior

- **dialogue:** active 4 (blocked 1)
- **tool:** active 4 (blocked 1)
- **fuzz:** active 3 (blocked 0)
- **memory:** active 4 (blocked 1)

- **Live chat cases passed:** 3/3

## How to explain in interviews

1. **Cheap gate** catches regressions without spending tokens (intent clarify, tool policy, citations).
2. **Full gate** samples live Agent A (research job) + Agent B (chat tools).
3. **Nightly / portfolio** measures quality with a **pillar ledger**: SimpleQA topic-stratified factuality + hallucination MAJOR rate (full 70) + product JSONL.
4. Never merge pillars into one “overall accuracy”.
5. Metrics are written to `evals/results/*_latest.json` for audit/repro.

See [PORTFOLIO.md](../PORTFOLIO.md) for the full narrative.
