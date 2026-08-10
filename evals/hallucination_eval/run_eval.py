"""
Run GPT-Researcher queries and evaluate them for hallucination.

Default judge is Matpool-friendly lite grader (--judge lite).
Optional --judge judges uses the original `judges` library (needs OpenAI).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "evals") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "evals"))

load_dotenv(REPO_ROOT / ".env")

from _common import resolve_sample_seed, seeded_sample  # noqa: E402
from gpt_researcher.agent import GPTResearcher  # noqa: E402
from gpt_researcher.utils.enum import ReportSource, ReportType, Tone  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = "evals/hallucination_eval/results"
DEFAULT_QUERIES_FILE = "evals/hallucination_eval/inputs/search_queries.jsonl"


class ResearchEvaluator:
    def __init__(self, queries_file: str = DEFAULT_QUERIES_FILE, judge: str = "lite"):
        self.queries_file = Path(queries_file)
        if judge == "judges":
            from evals.hallucination_eval.evaluate import HallucinationEvaluator

            self.hallucination_evaluator = HallucinationEvaluator()
        else:
            from _grader_llm import build_grader_chat_model
            from evals.hallucination_eval.evaluate_lite import LiteHallucinationEvaluator

            self.hallucination_evaluator = LiteHallucinationEvaluator(
                build_grader_chat_model()
            )

    def load_queries(
        self, num_queries: Optional[int] = None, seed: int | None = None
    ) -> List[str]:
        queries = []
        with open(self.queries_file, encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                queries.append(data["question"])
        if num_queries and num_queries < len(queries):
            sample_seed = resolve_sample_seed(seed)
            return seeded_sample(queries, num_queries, seed=sample_seed)
        return queries

    async def run_research(self, query: str) -> Dict:
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
        research_result = await researcher.conduct_research()
        report = await researcher.write_report()
        return {
            "query": query,
            "report": report,
            "context": research_result,
            "cost": researcher.get_costs(),
            "sources": researcher.get_source_urls(),
        }

    def evaluate_research(self, research_data: Dict, output_dir: Optional[str] = None) -> Dict:
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        # Keep list/dict context intact — do NOT str(list) (repr truncates to ~1 doc). :-)
        source_text = research_data.get("context")
        if not source_text:
            eval_result = {
                "input": research_data["query"],
                "output": research_data["report"],
                "source": "No source text available",
                "is_hallucination": None,
                "reasoning": "Evaluation skipped - no source text available",
            }
        else:
            eval_result = self.hallucination_evaluator.evaluate_response(
                model_output=research_data["report"],
                source_text=source_text,
            )
            eval_result["input"] = research_data["query"]
            eval_result["cost"] = research_data.get("cost")
            eval_result["source_count"] = len(research_data.get("sources") or [])

        os.makedirs(output_dir, exist_ok=True)
        records_file = Path(output_dir) / "evaluation_records.jsonl"
        with open(records_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(eval_result, ensure_ascii=False) + "\n")
        return eval_result


async def main_async(
    num_queries: int, output_dir: str, judge: str, seed: int | None = None
) -> dict:
    evaluator = ResearchEvaluator(judge=judge)
    sample_seed = resolve_sample_seed(seed)
    queries = evaluator.load_queries(num_queries, seed=sample_seed)
    logger.info(
        "Selected %s queries for evaluation (seed=%s)", len(queries), sample_seed
    )

    all_results = []
    total_hallucinated = 0
    total_responses = 0
    total_evaluated = 0
    severity_counts = {"MAJOR": 0, "MINOR": 0, "NONE": 0, "UNKNOWN": 0}

    for query in queries:
        try:
            logger.info("Processing query: %s", query)
            research_data = await evaluator.run_research(query)
            eval_results = evaluator.evaluate_research(research_data, output_dir=output_dir)
            all_results.append(eval_results)
            total_responses += 1
            if eval_results.get("is_hallucination") is not None:
                total_evaluated += 1
                if eval_results["is_hallucination"]:
                    total_hallucinated += 1
            sev = (eval_results.get("severity") or "UNKNOWN").upper()
            if sev not in severity_counts:
                sev = "UNKNOWN"
            severity_counts[sev] += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("Error processing query '%s': %s", query, exc)
            all_results.append({"input": query, "error": str(exc), "is_hallucination": None})

    hallucination_rate = (
        total_hallucinated / total_evaluated if total_evaluated > 0 else None
    )
    aggregate_results = {
        "suite": "hallucination",
        "judge": judge,
        "judge_mode": "multi_source_evidence_pack_major_only",
        "sample_seed": sample_seed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_queries": len(queries),
        "successful_queries": len([r for r in all_results if "error" not in r]),
        "total_responses": total_responses,
        "total_evaluated": total_evaluated,
        "total_hallucinated": total_hallucinated,
        "hallucination_rate": hallucination_rate,
        "severity_counts": severity_counts,
        "total_cost": sum(float(r.get("cost") or 0) for r in all_results),
        "results": all_results,
    }

    os.makedirs(output_dir, exist_ok=True)
    aggregate_file = Path(output_dir) / "aggregate_results.json"
    with open(aggregate_file, "w", encoding="utf-8") as f:
        json.dump(aggregate_results, f, indent=2, ensure_ascii=False)

    latest = REPO_ROOT / "evals" / "results" / "hallucination_latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(
        json.dumps(aggregate_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== Evaluation Summary ===")
    print(f"Queries processed: {len(queries)}")
    print(f"Responses evaluated: {total_evaluated}")
    if hallucination_rate is not None:
        print(f"Hallucination rate: {hallucination_rate * 100:.1f}%")
    print(f"Wrote {latest}")
    return aggregate_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GPT-Researcher hallucination evaluation")
    parser.add_argument("-n", "--num-queries", type=int, default=5)
    parser.add_argument("-o", "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--judge",
        choices=["lite", "judges"],
        default="lite",
        help="lite=Matpool ChatOpenAI judge; judges=original HaluEval library",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Sample seed (default: EVAL_SAMPLE_SEED or 42)",
    )
    args = parser.parse_args()
    summary = asyncio.run(
        main_async(args.num_queries, args.output_dir, args.judge, seed=args.seed)
    )
    if summary.get("total_evaluated", 0) == 0 and summary.get("successful_queries", 0) == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
