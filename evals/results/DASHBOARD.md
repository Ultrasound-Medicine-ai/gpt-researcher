# Project-2 evaluation dashboard

- Generated (UTC): `2026-08-11T02:39:31.518381+00:00`
- Regression queue size: **63**
- Trace spans indexed: **8**

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

## Perf P95

- PASS `perf-chat-p95-001` mode=schema
- PASS `perf-job-queue-p95-001` mode=schema

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
