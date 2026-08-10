# Project 2 — Evaluation gates

Validates Project 1 (research + chat SaaS) across seven pillars.
Upstream open-source suites cover **Agent A (reports)** only; dialogue / tools / memory are Project-2 additions.

## Seven pillars

| Pillar | Suite dir | Cheap (PR) | Full / Nightly |
|--------|-----------|------------|----------------|
| 1 Dialogue coverage | `dialogue_eval/` | mock multi-turn JSONL | live `/api/chat` sample |
| 2 Tool chain | `tool_eval/` | mock tool selection + params | live tools |
| 3 Memory / DST | `memory_eval/` | fixture + session soft-pass | live isolation |
| 4 Regression baselines | `harness_eval/` + SimpleQA + hallucination | offline report scorers | live research + factuality |
| 5 Fuzz | `fuzz_eval/` | offline noisy intent + tool forbid | periodic weakness mining |
| 6 Perf (P95) | `perf_eval/` | schema only (`blocked`) | release load check |
| 7 Tracing / metrics | `results/` JSON | gate summary artifact | dashboards later |

## Gate layers

```bash
# cheap — required before merge / phase complete (Python >= 3.10)
# conda activate gptresearcher
python evals/run_gates.py --suite cheap

# full — staging / manual (costs money); includes live chat if API is up
python evals/run_gates.py --suite full --limit 1

# nightly — SimpleQA + hallucination (expensive)
python evals/run_gates.py --suite nightly --num-examples 3

# portfolio pack — resume metrics in one shot
python evals/run_portfolio.py --num-examples 3
# or: python evals/run_nightly.py --num-examples 5
```

### cheap contents

1. `pytest` harness-related unit tests (no LLM)
2. `harness_eval --suite cheap` (offline report fixtures)
3. `dialogue_eval` / `tool_eval` / `memory_eval` cheap mock runners
4. `fuzz_eval` cheap offline runner (vague referents / ASR noise → no silent report)

Must exit 0. Session probes soft-pass if API is down.

CI: `.github/workflows/evals-cheap.yml` runs this suite on PRs that touch evals / planning intent / related tests.

### full contents

- `harness_eval --suite full` (live research, limited)
- Optional live chat sample when `EVAL_LIVE_CHAT=1`

### nightly contents

- `harness_eval --suite nightly` reminder path
- `simple_evals` (OpenAI SimpleQA CSV — shared with upstream)
- `hallucination_eval` (~70 research queries — shared with upstream)

## Case status

Cases use `status: active | blocked`.

- `active` — counted in the suite gate
- `blocked` — skipped until the matching Project-1 feature ships (e.g. in-chat PDF upload, `search_knowledge` tool)

## Upstream datasets (from open-source GPT-Researcher)

Reusable for **Agent A** nightly only:

- `simple_evals/problems/Simple QA Test Set.csv` — short-form factuality
- `hallucination_eval/inputs/search_queries.jsonl` — report faithfulness probes
- `simple_evals/logs/` — historical SimpleQA baseline (100 problems, 2025-02-22)

**Not** in upstream: dialogue, tool-calling, memory DST, fuzz, P95.

## Quality invariants (carry from harness)

- Harness / Project-2 runners **evaluate** outputs; they do not change generation prompts.
- Infrastructure (PG / Redis / MinIO) optional for cheap offline paths.
- LLM-as-judge (if used later) must be human-calibrated each release — do not ship on judge scores alone.

## Metrics artifacts

Cheap/full/nightly write a summary under `evals/results/gate_<suite>_<timestamp>.json`
(success rates, failures, skipped blocked cases). Tracing dashboards are out of scope for Phase 1.
