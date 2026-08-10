# GPT-Researcher Evaluations (Project 1 + Project 2)

This directory holds evaluation tools for GPT-Researcher.

- **Upstream (open source):** report factuality (`simple_evals`) and faithfulness (`hallucination_eval`).
- **Secondary (Project 1 harness):** product report regressions (`harness_eval`).
- **Project 2:** dialogue, tools, memory, fuzz cheap gates, perf stubs, and unified gates (`run_gates.py`).

See **[GATES.md](./GATES.md)** for cheap / full / nightly commands and pillar mapping.

## Quick start (cheap gate)

From repo root (Python >= 3.10; use `conda activate gptresearcher`):

```bash
python evals/run_gates.py --suite cheap
```

On Windows without activating conda:

```bash
D:\anaconda3\envs\gptresearcher\python.exe evals/run_gates.py --suite cheap
```

Nightly / portfolio sampling is reproducible via `--seed` or `EVAL_SAMPLE_SEED` (default **42**).

## Layout

| Path | Role |
|------|------|
| `simple_evals/` | OpenAI SimpleQA-style short-form factuality (Agent A) |
| `hallucination_eval/` | Report vs sources hallucination rate (Agent A) |
| `harness_eval/` | Offline/live report product scorers (language, cites, session) |
| `dialogue_eval/` | Multi-turn chat intent / clarify / refuse |
| `tool_eval/` | Tool selection + argument contracts |
| `memory_eval/` | Session isolation + slot consistency |
| `fuzz_eval/` | Adversarial inputs + weaknesses → promote loop |
| `perf_eval/` | P95 gates (cheap schema / full live chat|jobs) |
| `dashboard/` | Metrics board + regression queue + trace index |
| `run_gates.py` | Unified `--suite cheap\|full\|nightly` entrypoint |
| `run_portfolio.py` | One-shot pack → resume metrics (`PORTFOLIO_METRICS.md`) |
| `PORTFOLIO.md` | Interview / resume narrative |
| `results/` | Gate JSON + `DASHBOARD.md` artifacts |

## Upstream dataset note

A vanilla open-source checkout only ships SimpleQA + hallucination query sets.
Those measure **research reports**, not Chat tool-calling or memory DST.
Project 2 adds the missing pillars beside (not inside) those suites.

## Simple Evaluations (`simple_evals/`)

Adapted from [OpenAI simple-evals / SimpleQA](https://github.com/openai/simple-evals).

```bash
cd evals/simple_evals
pip install -r requirements.txt
# from repo root:
python evals/simple_evals/run_eval.py --num_examples 5
```

Historical baseline log (when present): `simple_evals/logs/SimpleQA Eval 100 Problems 2-22-25.txt`.

## Hallucination Evaluation (`hallucination_eval/`)

Compares generated reports to source materials.

```bash
python evals/hallucination_eval/run_eval.py -n 5
```

Inputs: `hallucination_eval/inputs/search_queries.jsonl` (~70 research questions).

## Product Harness (`harness_eval/`)

JSONL harness for report language, citations, retrieval tokens, session isolation.
Does **not** replace SimpleQA / hallucination.

```bash
python evals/harness_eval/run_eval.py --suite cheap
python evals/harness_eval/run_eval.py --suite full --limit 1
```

Companion unit tests (no LLM):

```bash
python -m pytest tests/test_harness_scorers.py tests/test_deterministic_cite.py tests/test_citation_registry.py tests/test_report_language.py -q
```

## Project 2 pillars (cheap mock)

```bash
python evals/dialogue_eval/run_eval.py --suite cheap
python evals/tool_eval/run_eval.py --suite cheap
python evals/memory_eval/run_eval.py --suite cheap
```

Prefer the unified gate:

```bash
python evals/run_gates.py --suite cheap
```
