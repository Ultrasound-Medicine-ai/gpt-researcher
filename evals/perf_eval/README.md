# Perf eval (Project 2)

P95 latency gates.

```bash
# cheap — schema + offline p95 helper (no API)
python evals/perf_eval/run_eval.py --suite cheap

# full — concurrent live /api/chat (soft-skip if API down)
python evals/perf_eval/run_eval.py --suite full --base-url http://127.0.0.1:8000

# optional expensive job queue P95
python evals/perf_eval/run_eval.py --suite full --include-jobs --concurrency 2

# controlled capacity + cost (Chat soak req/s + short/medium Job cost)
# NOT production QPS / online average cost — see CAPACITY_COST.md caveats
python evals/perf_eval/run_capacity_cost.py --chat-duration-sec 1800 --chat-concurrency 5 --short-n 15 --medium-n 8
```

Artifacts:
- `evals/results/perf_latest.json` (P95 gates)
- `evals/results/capacity_cost_latest.json` + `evals/results/CAPACITY_COST.md` (throughput/cost)
