"""
Harness runner: web-first research with optional local PDF cases.

Usage (from repo root):
    conda activate gptresearcher
    python evals/harness_eval/run_eval.py
    python evals/harness_eval/run_eval.py --limit 2
    python evals/harness_eval/run_eval.py --only web-001

Hybrid cases copy PDFs from evals/harness_eval/fixtures/ into a staging folder.
Web cases do not require uploads.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import ReportType, Tone

HARNESS_DIR = Path(__file__).resolve().parent
DEFAULT_CASES = HARNESS_DIR / "test_cases.jsonl"
FIXTURES_DIR = HARNESS_DIR / "fixtures"
STAGING_DIR = HARNESS_DIR / "staging"
RESULTS_DIR = HARNESS_DIR / "results"


def load_cases(path: Path, only_id: str | None, limit: int | None) -> list[dict]:
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if only_id and case.get("id") != only_id:
                continue
            cases.append(case)
    if limit is not None:
        cases = cases[:limit]
    return cases


def clear_staging() -> None:
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)


def stage_fixtures(fixture_names: list[str]) -> list[str]:
    clear_staging()
    staged = []
    for name in fixture_names:
        src = FIXTURES_DIR / name
        if not src.is_file():
            raise FileNotFoundError(
                f"Fixture not found: {src}. Place PDFs under evals/harness_eval/fixtures/"
            )
        dest = STAGING_DIR / name
        shutil.copy2(src, dest)
        staged.append(name)
    return staged


def check_keywords(report: str, keywords: list[str]) -> dict[str, bool]:
    lower = report.lower()
    return {kw: kw.lower() in lower for kw in keywords}


async def run_case(case: dict) -> dict:
    case_id = case["id"]
    question = case["question"]
    report_source = case.get("report_source", "web")
    min_sources = int(case.get("min_sources", 0))
    must_mention = case.get("must_mention") or []

    staged_files: list[str] = []
    if report_source == "hybrid":
        fixtures = case.get("fixtures") or []
        if not fixtures:
            raise ValueError(
                f"Case {case_id}: hybrid mode requires 'fixtures' list in test_cases.jsonl"
            )
        staged_files = stage_fixtures(fixtures)
        os.environ["DOC_PATH"] = str(STAGING_DIR)
    elif report_source == "web":
        clear_staging()
    else:
        raise ValueError(
            f"Case {case_id}: unsupported report_source '{report_source}'. "
            "Use 'web' or 'hybrid'."
        )

    started = time.time()
    researcher = GPTResearcher(
        query=question,
        report_type=ReportType.ResearchReport.value,
        report_source=report_source,
        tone=Tone.Objective,
        verbose=True,
    )
    await researcher.conduct_research()
    report = await researcher.write_report()
    elapsed = time.time() - started

    sources = researcher.get_source_urls()
    keyword_hits = check_keywords(report, must_mention)
    passed = True
    failures: list[str] = []

    if min_sources and len(sources) < min_sources:
        passed = False
        failures.append(f"expected min_sources>={min_sources}, got {len(sources)}")

    missing = [k for k, hit in keyword_hits.items() if not hit]
    if missing:
        passed = False
        failures.append(f"missing keywords: {missing}")

    return {
        "id": case_id,
        "report_source": report_source,
        "question": question,
        "fixtures": staged_files,
        "passed": passed,
        "failures": failures,
        "source_count": len(sources),
        "sources": sources[:20],
        "report_length": len(report),
        "cost": researcher.get_costs(),
        "elapsed_seconds": round(elapsed, 1),
        "keyword_hits": keyword_hits,
        "report_preview": report[:500],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="GPT Researcher harness (web + optional PDF)")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", type=str, default=None, help="Run a single case id")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_cases(args.cases, args.only, args.limit)
    if not cases:
        print("No test cases to run.")
        return

    print(f"Running {len(cases)} harness case(s)...")
    results = []
    for case in cases:
        print(f"\n--- {case['id']} ({case.get('report_source', 'web')}) ---")
        print(case["question"])
        try:
            result = await run_case(case)
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status} | sources={result['source_count']} | {result['elapsed_seconds']}s")
            if result["failures"]:
                print("  failures:", "; ".join(result["failures"]))
        except Exception as exc:
            result = {
                "id": case.get("id"),
                "report_source": case.get("report_source"),
                "question": case.get("question"),
                "passed": False,
                "error": str(exc),
            }
            print(f"ERROR: {exc}")
        results.append(result)

    ts = time.strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"run_{ts}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    passed = sum(1 for r in results if r.get("passed"))
    print(f"\nSummary: {passed}/{len(results)} passed")
    print(f"Results: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
