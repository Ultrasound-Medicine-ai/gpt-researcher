# Perf eval (Project 2)

Latency / concurrency gates (P95). Still **blocked** — needs a live load harness
(concurrent `/api/chat` and research jobs). Schema + cases live in `cases.jsonl`
until that runner ships.

```bash
# later:
python evals/perf_eval/run_eval.py --suite full
```

Cheap CI does **not** run perf (would need a live API and burn wall time).
