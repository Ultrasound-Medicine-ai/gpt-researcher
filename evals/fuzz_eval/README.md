# Fuzz eval (Project 2)

Adversarial / noisy dialogue inputs exercised **offline** (no live LLM).

```bash
python evals/fuzz_eval/run_eval.py --suite cheap
```

## Systematic recycle loop

```text
fuzz fail → weaknesses.jsonl → promote_weaknesses.py → active cases → cheap gate
```

```bash
# after a failing fuzz run (auto-appends weaknesses.jsonl)
python evals/fuzz_eval/promote_weaknesses.py --dry-run
python evals/fuzz_eval/promote_weaknesses.py --limit 5
```

Active seed cases: vague referent, ASR-noisy SSE, multi-task (no silent report).
