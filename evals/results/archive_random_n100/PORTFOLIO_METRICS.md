# Portfolio evaluation metrics

- Generated (UTC): `2026-08-10T14:15:47.167227+00:00`
- Sample size (SimpleQA requested / hallucination requested): **10**
- Sample seed: **None**
- SimpleQA sample mode: **random**

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

- **accuracy (among attempted):** 70.0%
- **F1:** 0.700
- **correct rate:** 70.0% (10 graded)
- **effective_n / mode:** 10 / `random`
- **topic strata:** `{}`
- **answer_type mix (report-only):** `{}`
- **cost:** $0.4749

### B — Faithfulness (hallucination)

- **MAJOR hallucination detection rate:** 50.0% (5/10 evaluated)
- **effective_n:** 10 (requested 10)
- **Judge mode:** `multi_source_evidence_pack_major_only`
- **Severity mix:** MAJOR 5 / MINOR 1 / NONE 4
- **cost:** $0.5335

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
