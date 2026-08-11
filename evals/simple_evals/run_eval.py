"""
Run GPT-Researcher on SimpleQA samples and grade with an LLM judge.

Env-flexible: works with Matpool (MATPOOL_API_KEY + MATPOOL_BASE_URL) or OpenAI.
LANGCHAIN_API_KEY is optional.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "evals") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "evals"))

load_dotenv(REPO_ROOT / ".env")

from _grader_llm import build_grader_chat_model  # noqa: E402
from evals.simple_evals.simpleqa_eval import SimpleQAEval  # noqa: E402
from gpt_researcher.agent import GPTResearcher  # noqa: E402
from gpt_researcher.utils.enum import ReportSource, ReportType, Tone  # noqa: E402


def _require_research_keys() -> None:
    if not (
        os.getenv("MATPOOL_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    ):
        raise ValueError(
            "Need MATPOOL_API_KEY, DASHSCOPE_API_KEY, or OPENAI_API_KEY for research+grading"
        )
    if not (os.getenv("TAVILY_API_KEY") or os.getenv("TAVILY_API_KEYS")):
        raise ValueError("TAVILY_API_KEY (or TAVILY_API_KEYS) required for web research")


async def evaluate_single_query(query: str, evaluator: SimpleQAEval) -> dict:
    print(f"\nEvaluating query: {query}")
    total_words = int(os.getenv("EVAL_TOTAL_WORDS") or "350")
    os.environ["TOTAL_WORDS"] = str(total_words)
    researcher = GPTResearcher(
        query=query,
        report_type=ReportType.ResearchReport.value,
        report_format="markdown",
        report_source=ReportSource.Web.value,
        tone=Tone.Objective,
        verbose=True,
    )
    context = await researcher.conduct_research()
    report = await researcher.write_report()

    example = next(ex for ex in evaluator.examples if ex.get("problem") == query)
    correct_answer = example["answer"]
    eval_result = evaluator.evaluate_example(
        {"problem": query, "answer": correct_answer, "predicted": report}
    )
    return {
        "query": query,
        "gold_answer": correct_answer,
        "context_length": len(context or ""),
        "report_length": len(report or ""),
        "cost": researcher.get_costs(),
        "sources": researcher.get_source_urls(),
        "evaluation_score": eval_result["score"],
        "evaluation_grade": eval_result["metrics"]["grade"],
        "report_preview": (report or "")[:400],
    }


async def main_async(
    num_examples: int,
    seed: int | None = None,
    sample_mode: str = "stratified",
) -> dict:
    from _common import resolve_sample_seed

    _require_research_keys()
    grader = build_grader_chat_model()
    sample_seed = resolve_sample_seed(seed)
    mode = (sample_mode or os.getenv("EVAL_SAMPLE_MODE") or "stratified").strip().lower()
    evaluator = SimpleQAEval(
        grader_model=grader,
        num_examples=num_examples,
        seed=sample_seed,
        sample_mode=mode,
    )
    results = []
    for example in evaluator.examples:
        query = example.get("problem")
        if not query:
            continue
        try:
            row = await evaluate_single_query(query, evaluator)
            row["topic"] = example.get("_topic")
            row["answer_type"] = example.get("_answer_type")
            results.append(row)
        except Exception as exc:  # noqa: BLE001
            print(f"✗ Error evaluating query: {exc}")
            results.append(
                {
                    "query": query,
                    "error": str(exc),
                    "topic": example.get("_topic"),
                    "answer_type": example.get("_answer_type"),
                }
            )

    successful = [r for r in results if "error" not in r]
    correct = sum(1 for r in successful if r.get("evaluation_grade") == "CORRECT")
    incorrect = sum(1 for r in successful if r.get("evaluation_grade") == "INCORRECT")
    not_attempted = sum(1 for r in successful if r.get("evaluation_grade") == "NOT_ATTEMPTED")
    n = len(successful) or 1
    attempted = correct + incorrect
    precision = correct / attempted if attempted else 0.0
    recall = correct / len(successful) if successful else 0.0
    f1 = (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )
    metrics = {
        "correct_rate": correct / n,
        "incorrect_rate": incorrect / n,
        "not_attempted_rate": not_attempted / n,
        "accuracy": precision,
        "f1": f1,
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "total_cost": sum(float(r.get("cost") or 0) for r in successful),
    }
    summary = {
        "suite": "simpleqa",
        "num_examples": num_examples,
        "effective_n": len(evaluator.examples),
        "sample_seed": sample_seed,
        "sample_mode": mode,
        "strata_counts": getattr(evaluator, "strata_counts", {}),
        "answer_type_counts": getattr(evaluator, "answer_type_counts", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "results": results,
    }

    print("\n=== AGGREGATE METRICS ===")
    print(json.dumps(metrics, indent=2))
    print(f"Accuracy: {metrics['accuracy']:.3f}")
    print(f"F1 Score: {metrics['f1']:.3f}")
    print(f"Total cost: ${metrics['total_cost']:.4f}")

    out_dir = REPO_ROOT / "evals" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "simpleqa_latest.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GPT-Researcher SimpleQA evaluation")
    parser.add_argument("--num_examples", type=int, default=1)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Sample seed (default: EVAL_SAMPLE_SEED or 42)",
    )
    parser.add_argument(
        "--sample-mode",
        choices=["stratified", "random"],
        default=None,
        help="stratified (default) = topic-proportional; random = uniform",
    )
    args = parser.parse_args()
    mode = args.sample_mode or os.getenv("EVAL_SAMPLE_MODE") or "stratified"
    summary = asyncio.run(
        main_async(args.num_examples, seed=args.seed, sample_mode=mode)
    )
    # Soft-fail only if zero successful graded rows
    if summary["metrics"]["successful"] == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
