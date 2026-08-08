# Harness gates

## cheap (required before merge / phase complete)

```bash
python -m pytest tests/test_harness_scorers.py tests/test_deterministic_cite.py tests/test_citation_registry.py tests/test_report_language.py -q
python evals/harness_eval/run_eval.py --suite cheap
```

Must exit 0. Offline cases only; session probe soft-passes if API is down.

## full (staging)

```bash
python evals/harness_eval/run_eval.py --suite full --limit 2
```

Live research — costs money/time; not for every PR.

## nightly (pre-release)

```bash
python evals/harness_eval/run_eval.py --suite nightly
# plus:
#   evals/simple_evals/run_eval.py --num_examples N
#   evals/hallucination_eval/run_eval.py -n N
```

## Quality invariant

Infrastructure (PostgreSQL / Redis / MinIO / PGVector / ARQ) is **optional**.

- Unset `DATABASE_URL` → JSON report store (legacy path)
- Unset `REDIS_URL` → in-process job fallback (same `run_agent`)
- Vector persist / object store / deterministic cite failures are **non-fatal**
- Report generation parameters are never altered by persistence wrappers
- **PostgreSQL is the job state source of truth** when configured; Redis is queue/cache only

## Human calibration (project 2)

LLM-as-judge scores must be spot-checked by humans on a fixed sample each release
(e.g. 20 cases). Record disagreements and adjust prompts/thresholds — do not ship
on judge scores alone.
