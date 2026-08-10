# Portfolio evaluation metrics

- Generated (UTC): `2026-08-10T09:07:04.591308+00:00`
- Sample size (SimpleQA / hallucination): **10**
- Hallucination judge: `lite` + multi-source evidence pack + **MAJOR-only**

## Gate layers

| Layer | Result | Notes |
|-------|--------|-------|
| cheap (offline) | PASS | dialogue/tool/memory/fuzz + report scorers |
| full harness | PASS | live research sample |
| live chat | PASS | `/api/chat` tool routing |
| SimpleQA | see metrics | factuality of research reports |
| Hallucination | see metrics | faithfulness vs retrieved evidence pack |

## Headline numbers (resume-friendly)

- **SimpleQA accuracy (among attempted):** 70.0%
- **SimpleQA F1:** 0.700
- **SimpleQA correct rate:** 70.0% (10 graded)
- **SimpleQA cost (sample):** $0.4749

- **Hallucination rate (MAJOR):** 50.0% (5/10 evaluated)
- **Severity mix:** MAJOR 5 / MINOR 1 / NONE 4
- **Hallucination sample cost:** $0.5335

- **Live chat cases passed:** 3/3

## How to explain in interviews

1. **Cheap gate** catches regressions without spending tokens (intent clarify, tool policy, citations).
2. **Full gate** samples live Agent A (research job) + Agent B (chat tools).
3. **Nightly / portfolio** measures quality: SimpleQA factuality + faithfulness judge against a **multi-source evidence pack** (MAJOR unsupported claims only).
4. Metrics are written to `evals/results/*_latest.json` for audit/repro.

See [PORTFOLIO.md](../PORTFOLIO.md) for the full narrative.
