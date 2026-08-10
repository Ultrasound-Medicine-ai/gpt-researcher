# Portfolio evaluation metrics

- Generated (UTC): `2026-08-10T08:05:47.058031+00:00`
- Sample size (SimpleQA / hallucination): **3**

## Gate layers

| Layer | Result | Notes |
|-------|--------|-------|
| cheap (offline) | PASS | dialogue/tool/memory + report scorers |
| full harness | PASS | live research sample |
| live chat | PASS | `/api/chat` tool routing |
| SimpleQA | see metrics | factuality of research reports |
| Hallucination | see metrics | faithfulness vs retrieved context |

## Headline numbers (resume-friendly)

- **SimpleQA accuracy (among attempted):** 100.0%
- **SimpleQA F1:** 0.800
- **SimpleQA correct rate:** 66.7% (3 graded)
- **SimpleQA cost (sample):** $0.1700

- **Hallucination rate:** 66.7% (2/3 evaluated)
- **Hallucination sample cost:** $0.1699

- **Live chat cases passed:** 3/3

## How to explain in interviews

1. **Cheap gate** catches regressions without spending tokens (intent clarify, tool policy, citations).
2. **Full gate** samples live Agent A (research job) + Agent B (chat tools).
3. **Nightly / portfolio** measures quality: SimpleQA factuality + faithfulness judge.
4. Metrics are written to `evals/results/*_latest.json` for audit/repro.

See [PORTFOLIO.md](./PORTFOLIO.md) for the full narrative.
