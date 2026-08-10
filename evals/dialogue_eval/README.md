# Dialogue eval

Multi-turn chat coverage: intent, clarify, refuse, report-vs-search routing.

Cheap runner is **mock-only** (uses `jobs.planning_context.resolve_report_intent` for
SSE disambiguation; no live Chat LLM).

```bash
python evals/dialogue_eval/run_eval.py --suite cheap
```
