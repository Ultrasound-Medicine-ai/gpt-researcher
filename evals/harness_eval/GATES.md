# Harness gates (Agent A reports)

Canonical Project-2 gate doc: **[../GATES.md](../GATES.md)**.

## cheap (legacy direct invoke)

```bash
python -m pytest tests/test_harness_scorers.py tests/test_deterministic_cite.py tests/test_citation_registry.py tests/test_report_language.py -q
python evals/harness_eval/run_eval.py --suite cheap
```

Prefer:

```bash
python evals/run_gates.py --suite cheap
python evals/run_portfolio.py --num-examples 3   # resume metrics pack
```

See [PORTFOLIO.md](./PORTFOLIO.md) for interview narrative.

## full / nightly

See [../GATES.md](../GATES.md).

## Quality invariant

Infrastructure (PostgreSQL / Redis / MinIO / PGVector / ARQ) is **optional** for offline cases.

- Unset `DATABASE_URL` → JSON report store (legacy path)
- Enqueue failure → Job stays `pending_dispatch` + **503**; production never `asyncio.create_task` (`ALLOW_IN_PROCESS_RESEARCH_FALLBACK=false`)
- UI path: `POST /api/jobs/research` then poll `GET /api/jobs/{id}` every 1–2s
- Report generation parameters are never altered by persistence wrappers
- **PostgreSQL is the job state source of truth** when configured; Redis is queue/cache only

## Human calibration

LLM-as-judge scores must be spot-checked by humans on a fixed sample each release.
Do not ship on judge scores alone.
