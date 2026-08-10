# Fuzz eval (Project 2)

Adversarial / noisy dialogue inputs exercised **offline** (no live LLM).

Cheap runner calls `resolve_report_intent` plus a mock tool policy so garbled
ASR / vague referents cannot silently open `create_research_report`.

```bash
# from repo root
python evals/fuzz_eval/run_eval.py --suite cheap

# or via unified gates
python evals/run_gates.py --suite cheap
```

Active cases:

| id | Intent |
|----|--------|
| `fuzz-ambiguous-referent-001` | Vague “把那个再详细一点” → no report tool |
| `fuzz-asr-noise-001` | Noisy “调演 SSE”（调研 ASR 噪声）→ still clarify SSE senses |

Perf / live fuzz load tests remain out of scope here.
