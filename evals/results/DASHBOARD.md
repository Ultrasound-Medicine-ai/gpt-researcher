# Project-2 evaluation dashboard

- Generated (UTC): `2026-08-10T11:37:19.493790+00:00`
- Regression queue size: **8**
- Trace spans indexed: **6**

## Gate layers

| Layer | OK | Notes |
|-------|----|-------|
| cheap | True | offline dialogue/tool/memory/fuzz/perf-schema |
| portfolio | True | resume pack present=yes |
| live chat | True | 3/3 |
| perf | True | cheap |

## Quality headlines

- SimpleQA accuracy: **0.7** (seed=None)
- SimpleQA F1: **0.7**
- Hallucination rate: **0.5** (judge=multi_source_evidence_pack_major_only)
- Hallucination severity: `{'MAJOR': 5, 'MINOR': 1, 'NONE': 4, 'UNKNOWN': 0}`

## Perf P95

- PASS `perf-chat-p95-001` mode=schema
- PASS `perf-job-queue-p95-001` mode=schema

## Regression queue (top 20)

- `simpleqa_incorrect` / `In Season 1 of the American version of "Big Brother," who was the saboteur?` ← simpleqa 
- `simpleqa_incorrect` / `On what day, month, and year did the Philippines ratify the Southeast Asian Nuclear-Weapon-Free Zone Treaty?` ← simpleqa 
- `simpleqa_incorrect` / `In 1979, who won the Triple Tiara?` ← simpleqa 
- `hallucination_major` / `Find live coverage or recaps of the 2025 NVIDIA GTC keynote.` ← hallucination 
- `hallucination_major` / `How does OpenAI’s enterprise pricing compare to Anthropic’s?` ← hallucination 
- `hallucination_major` / `What were the main announcements at Google I/O this year?` ← hallucination 
- `hallucination_major` / `Which companies are leading the development of AI agents?` ← hallucination 
- `hallucination_major` / `What’s the difference between LangChain, LlamaIndex, and CrewAI?` ← hallucination 

## Closed loop

1. Run gates / portfolio / fuzz → artifacts under `evals/results/`.
2. `python evals/dashboard/build_dashboard.py` rebuilds this page + queue.
3. Fuzz failures append `evals/fuzz_eval/weaknesses.jsonl`; promote with `python evals/fuzz_eval/promote_weaknesses.py`.
4. Trace index: `evals/results/trace_index.json` (gate/perf spans).
