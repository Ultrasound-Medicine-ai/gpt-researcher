# Portfolio evaluation metrics

- Generated (UTC): `2026-08-10T11:46:54Z` (perf refreshed)
- Sample size (SimpleQA / hallucination): **10**
- Hallucination judge: `lite` + multi-source evidence pack + **MAJOR-only**

## Gate layers

| Layer | Result | Notes |
|-------|--------|-------|
| cheap (offline) | PASS | dialogue/tool/memory/fuzz/perf-schema + dashboard |
| full harness | PASS | live research sample |
| live chat | PASS | `/api/chat` tool routing 3/3 |
| Chat P95 (live) | PASS | p95 ≈ **2395 ms** (max 8000 ms, concurrency=5, n=10) |
| Job P95 | SKIP | enable with `--include-jobs` / `EVAL_PERF_JOBS=1` |
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
- **Chat P95:** 2395 ms (threshold 8000 ms)

## How to explain in interviews

1. **Cheap gate** catches regressions without spending tokens (intent clarify, tool policy, fuzz, citations).
2. **Full gate** samples live Agent A/B and measures Chat P95 under light concurrency.
3. **Nightly / portfolio** measures quality: SimpleQA + multi-source faithfulness (MAJOR only).
4. Dashboard rebuilds `DASHBOARD.md` + `regression_queue.jsonl` for closed-loop fixes.

See [PORTFOLIO.md](../PORTFOLIO.md) for the full narrative.
