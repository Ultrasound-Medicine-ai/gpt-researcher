# Perf eval (Project 2)

P95 latency gates.

```bash
# cheap — schema + offline p95 helper (no API)
python evals/perf_eval/run_eval.py --suite cheap

# full — concurrent live /api/chat (soft-skip if API down)
python evals/perf_eval/run_eval.py --suite full --base-url http://127.0.0.1:8000

# optional expensive job queue P95
python evals/perf_eval/run_eval.py --suite full --include-jobs --concurrency 3
```

Artifacts: `evals/results/perf_latest.json`.
