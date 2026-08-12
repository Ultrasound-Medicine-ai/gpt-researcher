# Project-2 evaluation dashboard

- Generated (UTC): `2026-08-12T03:52:45.272660+00:00`
- Regression queue size: **80**
- Trace spans indexed: **190**

## Gate layers

| Layer | OK | Notes |
|-------|----|-------|
| cheap | True | offline dialogue/tool/memory/fuzz/perf-schema |
| portfolio | True | resume pack present=yes |
| live chat | True | 3/3 |
| perf | True | cheap |

## Quality headlines

- SimpleQA accuracy: **0.8152173913043478** (seed=42, mode=stratified)
- SimpleQA F1: **0.7812500000000001**
- SimpleQA topic strata: `{'Art': 13, 'Geography': 10, 'History': 4, 'Music': 8, 'Other': 11, 'Politics': 16, 'Science and technology': 20, 'Sports': 8, 'TV shows': 7, 'Video games': 3}`
- Hallucination rate: **0.6571428571428571** (judge=multi_source_evidence_pack_major_only, effective_n=70)
- Hallucination severity: `{'MAJOR': 46, 'MINOR': 8, 'NONE': 16, 'UNKNOWN': 0}`
- Hallucination by_bucket: `{'fresh_news': {'n': 9, 'evaluated': 9, 'major': 6, 'hallucinated': 6, 'major_rate': 0.6666666666666666, 'hallucination_rate': 0.6666666666666666}, 'howto_technical': {'n': 16, 'evaluated': 16, 'major': 10, 'hallucinated': 10, 'major_rate': 0.625, 'hallucination_rate': 0.625}, 'landscape_vendor': {'n': 6, 'evaluated': 6, 'major': 5, 'hallucinated': 5, 'major_rate': 0.8333333333333334, 'hallucination_rate': 0.8333333333333334}, 'other': {'n': 33, 'evaluated': 33, 'major': 21, 'hallucinated': 21, 'major_rate': 0.6363636363636364, 'hallucination_rate': 0.6363636363636364}, 'pricing_compare': {'n': 6, 'evaluated': 6, 'major': 4, 'hallucinated': 4, 'major_rate': 0.6666666666666666, 'hallucination_rate': 0.6666666666666666}}`

## Intent routing

### Cheap deterministic routing

- Accuracy: **1.0**; macro P/R/F1: **1.0 / 1.0 / 1.0**
- Route false-positive rate: **0.0** (0/6)
- Actual false-creation rate: **0.0** (0/6)
- Guarded route false positives: **0**

| Intent | Precision | Recall | F1 | Support |
|--------|-----------|--------|----|---------|
| `answer_from_report` | 1.0 | 1.0 | 1.0 | 1 |
| `clarify` | 1.0 | 1.0 | 1.0 | 1 |
| `create_research_report` | 1.0 | 1.0 | 1.0 | 4 |
| `quick_search` | 1.0 | 1.0 | 1.0 | 4 |

Confusion matrix (expected → predicted): `{'answer_from_report': {'answer_from_report': 1, 'clarify': 0, 'create_research_report': 0, 'quick_search': 0}, 'clarify': {'answer_from_report': 0, 'clarify': 1, 'create_research_report': 0, 'quick_search': 0}, 'create_research_report': {'answer_from_report': 0, 'clarify': 0, 'create_research_report': 4, 'quick_search': 0}, 'quick_search': {'answer_from_report': 0, 'clarify': 0, 'create_research_report': 0, 'quick_search': 4}}`

### Live LLM routing

- Accuracy: **1.0**; macro P/R/F1: **1.0 / 1.0 / 1.0**
- Route false-positive rate: **0.0** (0/2)
- Actual false-creation rate: **0.0** (0/2)
- Guarded route false positives: **0**

| Intent | Precision | Recall | F1 | Support |
|--------|-----------|--------|----|---------|
| `answer_from_report` | 1.0 | 1.0 | 1.0 | 1 |
| `clarify` | 1.0 | 1.0 | 1.0 | 1 |
| `create_research_report` | 1.0 | 1.0 | 1.0 | 1 |

Confusion matrix (expected → predicted): `{'answer_from_report': {'answer_from_report': 1, 'clarify': 0, 'create_research_report': 0}, 'clarify': {'answer_from_report': 0, 'clarify': 1, 'create_research_report': 0}, 'create_research_report': {'answer_from_report': 0, 'clarify': 0, 'create_research_report': 1}}`

## Offline Agent evaluation harness (seed=42)

| Pillar | N | Pass / fail | Key ratios | Blocked | Latest run |
|--------|---|-------------|------------|---------|------------|
| intent | 80 | 72 / 8 | n/a | 0 | local offline |
| multiturn | 20 | 20 / 0 | turn_accuracy=1.0, intent_consistency=1.0, slot_constraint_retention=1.0 | 0 | local offline |
| tool_chain | 20 | 20 / 0 | case_pass_rate=1.0, duplicate_side_effect_count=0, tool_selection_accuracy=1.0 | 0 | local offline |
| fuzz | 30 | 30 / 0 | overall_pass_rate=1.0, unsafe_side_effect_count=0, per_category={'ambiguous_reference': 6, 'asr_noise': 6, 'typo': 6, 'multi_task': 6, 'redundant_noise': 6} | 0 | local offline |
| memory | 20 | 20 / 0 | case_pass_rate=1.0, duplicate_side_effect_count=0, memory_write_correctness=1.0 | 0 | local offline |
| security | 20 | 20 / 0 | blocked_attack_rate=1.0, unsafe_side_effect_count=0, per_category={'ignore previous instructions': 2, 'reveal the system prompt': 2, "read another user's job": 2, "read another user's artifact": 2, 'guess job_id': 2, 'create task as admin': 2, 'tool argument injection': 2, 'indirect prompt injection': 2, 'sensitive context exfiltration': 2, 'call an unauthorized tool': 2} | 0 | local offline |
| trace_replay | 8 | 0 / 0 | spans=190; reproducible_failures=0 | 0 | 2026-08-11T15:52:23.330130+00:00 |

## Perf P95

- PASS `perf-chat-p95-001` mode=schema
- PASS `perf-job-queue-p95-001` mode=schema

## Latest controlled evaluations

- `live_intent_expanded`: status=COMPLETED; N=24; `{'evaluated_requests': 24, 'labels': ['answer_from_report', 'clarify', 'create_research_report', 'quick_search'], 'confusion_matrix': {'answer_from_report': {'answer_from_report': 6, 'clarify': 0, 'create_research_report': 0, 'quick_search': 0}, 'clarify': {'answer_from_report': 0, 'clarify': 6, 'create_research_report': 0, 'quick_search': 1}, 'create_research_report': {'answer_from_report': 0, 'clarify': 0, 'create_research_report': 5, 'quick_search': 0}, 'quick_search': {'answer_from_report': 0, 'clarify': 0, 'create_research_report': 0, 'quick_search': 6}}, 'per_class': {'answer_from_report': {'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'support': 6}, 'clarify': {'precision': 1.0, 'recall': 0.8571, 'f1': 0.9231, 'support': 7}, 'create_research_report': {'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'support': 5}, 'quick_search': {'precision': 0.8571, 'recall': 1.0, 'f1': 0.9231, 'support': 6}}, 'accuracy': 0.9583, 'macro_precision': 0.9643, 'macro_recall': 0.9643, 'macro_f1': 0.9615, 'report_route_false_positives': 0, 'report_route_false_positive_rate': 0.0, 'false_report_creations': 0, 'non_create_requests': 19, 'non_create_requests_with_side_effect_observation': 19, 'false_report_creation_rate': 0.0, 'guarded_report_route_false_positives': 0, 'expected_create_requests_with_side_effect_observation': 5, 'missed_report_creations': 0, 'report_creation_success_rate': 1.0}`; 
- `live_intent_holdout`: status=COMPLETED; N=12; `{'evaluated_requests': 12, 'labels': ['answer_from_report', 'clarify', 'create_research_report', 'quick_search'], 'confusion_matrix': {'answer_from_report': {'answer_from_report': 2, 'clarify': 0, 'create_research_report': 0, 'quick_search': 0}, 'clarify': {'answer_from_report': 0, 'clarify': 3, 'create_research_report': 0, 'quick_search': 1}, 'create_research_report': {'answer_from_report': 0, 'clarify': 0, 'create_research_report': 3, 'quick_search': 0}, 'quick_search': {'answer_from_report': 0, 'clarify': 0, 'create_research_report': 0, 'quick_search': 3}}, 'per_class': {'answer_from_report': {'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'support': 2}, 'clarify': {'precision': 1.0, 'recall': 0.75, 'f1': 0.8571, 'support': 4}, 'create_research_report': {'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'support': 3}, 'quick_search': {'precision': 0.75, 'recall': 1.0, 'f1': 0.8571, 'support': 3}}, 'accuracy': 0.9167, 'macro_precision': 0.9375, 'macro_recall': 0.9375, 'macro_f1': 0.9285, 'report_route_false_positives': 0, 'report_route_false_positive_rate': 0.0, 'false_report_creations': 0, 'non_create_requests': 9, 'non_create_requests_with_side_effect_observation': 9, 'false_report_creation_rate': 0.0, 'guarded_report_route_false_positives': 0, 'expected_create_requests_with_side_effect_observation': 3, 'missed_report_creations': 0, 'report_creation_success_rate': 1.0}`; 
- `judge_stability`: status=BLOCKED; N=12; `{}`; current judge unavailable: ModuleNotFoundError: No module named 'langchain_openai'
- `judge_calibration`: status=BLOCKED; N=12; `{}`; 
- `retrieval`: status=COMPLETED; N=20; `{'recall_at_1': 1.0, 'recall_at_3': 1.0, 'recall_at_5': 1.0, 'mrr': 1.0}`; 
- `planning`: status=BLOCKED; N=0; `{}`; Standalone Planner could not initialize; no persisted plan is compatible with this evaluation set.
- `planning_holdout`: status=BLOCKED; N=0; `{}`; Standalone Planner could not initialize; no persisted plan is compatible with this evaluation set.

## Interpretation limits

- Live Intent results are controlled test cases, **not production accuracy**. The frozen pre-fix result remains in its JSON artifact for regression history but is not a current headline.
- Judge historical replay is **BLOCKED** because the original 70-case artifact retained only an 800-character evidence preview. New hallucination evaluations now persist `evidence_pack`; no historical evidence was fabricated or regenerated.
- Retrieval is document-level testing of the existing keyword fallback only; it does **not** represent PGVector semantic-retrieval quality.
- Planning metrics use the normalized scorer (`normalized_keyword_v2`) and existing Planner outputs; no Planner model was rerun during scorer correction.

## Planning by scenario

### planning (N=0)

| Scenario | N | Subgoal coverage | Constraint retention | Redundant | Irrelevant | Executable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
- failure case IDs: planner-initialization

### planning_holdout (N=0)

| Scenario | N | Subgoal coverage | Constraint retention | Redundant | Irrelevant | Executable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
- failure case IDs: planner-initialization


## Regression queue (top 20)

- `simpleqa_incorrect` / `In what month and year was William Bentinck, Duke of Portland, appointed as Chancellor of Oxford University?` ← simpleqa 
- `simpleqa_incorrect` / `What year was the municipality of Valparaíso, Antioquia, Colombia, founded?` ← simpleqa 
- `simpleqa_incorrect` / `In what year did Augustus De Morgan publish the article "Trochoidal Curve" in the Penny Cyclopaedia?` ← simpleqa 
- `simpleqa_incorrect` / `Who was the first openly bisexual state official in the USA?` ← simpleqa 
- `simpleqa_incorrect` / `In which episode of Community does Shirley Bennett say, "The Bible doesn't recognize divorce, Britta! When you marry a man, he's your man!"?` ← simpleqa 
- `simpleqa_incorrect` / `In Season 4, Episode 5 of Gossip Girl, what did Vanessa Abrams steal from Serena van der Woodsen in the coat check?` ← simpleqa 
- `simpleqa_incorrect` / `What is the height (in feet) of Taipei 101?` ← simpleqa 
- `simpleqa_incorrect` / `How many feet deep is the Mississippi River at its source, Lake Itasca?` ← simpleqa 
- `simpleqa_incorrect` / `In what year did the Met Gala first become a themed fashion event?` ← simpleqa 
- `simpleqa_incorrect` / `What's the first and last name of the person who sings Alastor's voice in the song "Alastor's Game"?` ← simpleqa 
- `simpleqa_incorrect` / `What position did the album "Expectations" by Bebe Rexha place in the 2018 US Billboard 200 year-end chart?` ← simpleqa 
- `simpleqa_incorrect` / `Why was Bessie Smith dismissed from Black Swan Records during auditions?` ← simpleqa 
- `simpleqa_incorrect` / `In which round was Martina Trevisan eliminated from the 2020 French Open – Women's Singles?` ← simpleqa 
- `simpleqa_incorrect` / `What part of the body do the eggs of moon jellies lodge in?` ← simpleqa 
- `simpleqa_incorrect` / `What is the name of Daniel arap Moi's mother?` ← simpleqa 
- `simpleqa_incorrect` / `What month, day, and year did the Wayback Machine begin fact-checking content?` ← simpleqa 
- `simpleqa_incorrect` / `How many girls are in "Girls on the Bridge," Munch's painting from 1900 (in the version where some of them are looking at the river)?` ← simpleqa 
- `hallucination_major` / `What are the top emerging startups in AI hardware in 2025?` ← hallucination 
- `hallucination_major` / `Compare pricing and features of the top vector database platforms.` ← hallucination 
- `hallucination_major` / `Summarize recent M&A activity in the healthtech sector.` ← hallucination 

## Closed loop

1. Run gates / portfolio / fuzz → artifacts under `evals/results/`.
2. `python evals/dashboard/build_dashboard.py` rebuilds this page + queue.
3. Fuzz failures append `evals/fuzz_eval/weaknesses.jsonl`; promote with `python evals/fuzz_eval/promote_weaknesses.py`.
4. Trace index: `evals/results/trace_index.json` (gate/perf spans).
