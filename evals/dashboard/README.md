# Project-2 dashboard / tracing loop

Aggregates local eval artifacts into a human-readable board and a regression queue.

```bash
python evals/dashboard/build_dashboard.py
```

Outputs under `evals/results/`:

| File | Role |
|------|------|
| `DASHBOARD.md` / `dashboard.html` | Metrics board |
| `regression_queue.jsonl` | Failures to fix / re-run |
| `trace_index.json` | Gate + perf span index for repro |

This is an **offline closed loop** (artifacts → board → queue), not a hosted APM.
Pipeline traces from `backend/trusted_report/tracing.py` can be pasted into the queue manually when investigating a single research job.
