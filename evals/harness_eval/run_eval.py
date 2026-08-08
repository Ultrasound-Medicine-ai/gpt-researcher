"""
Harness runner: web-first research with optional product-quality scorers.

Quality note: this harness evaluates outputs; it does not change generation.

Usage (from repo root):
    conda activate gptresearcher
    python evals/harness_eval/run_eval.py --suite cheap
    python evals/harness_eval/run_eval.py --limit 2
    python evals/harness_eval/run_eval.py --only web-001

Suites:
    cheap   — deterministic scorers + optional offline unit cases (default)
    full    — all JSONL cases including live research (expensive)
    nightly — alias for full + reminder to run simple_evals / hallucination_eval
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

HARNESS_DIR = Path(__file__).resolve().parent
DEFAULT_CASES = HARNESS_DIR / "test_cases.jsonl"
FIXTURES_DIR = HARNESS_DIR / "fixtures"
STAGING_DIR = HARNESS_DIR / "staging"
RESULTS_DIR = HARNESS_DIR / "results"
SCORERS_DIR = HARNESS_DIR / "scorers"

sys.path.insert(0, str(HARNESS_DIR))


def load_cases(path: Path, only_id: str | None, limit: int | None, suite: str) -> list[dict]:
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if only_id and case.get("id") != only_id:
                continue
            case_suite = case.get("suite", "full")
            if suite == "cheap" and case_suite not in ("cheap", "both"):
                continue
            if suite in ("full", "nightly") and case_suite == "session-only":
                # session cases run separately
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


def apply_scorers(report: str, case: dict, source_count: int) -> tuple[bool, list[str], dict]:
    from scorers.language import score_report_language
    from scorers.citations import score_citations
    from scorers.retrieval import score_must_mention

    failures: list[str] = []
    details: dict = {}
    expect = case.get("expect") or {}
    must_mention = case.get("must_mention") or expect.get("must_mention") or []

    if expect.get("lang") or expect.get("refs_heading"):
        ok, fails = score_report_language(report, expect)
        details["language"] = {"ok": ok, "failures": fails}
        if not ok:
            failures.extend(fails)

    if any(k in expect for k in ("min_bracket_cites", "cites_subseteq_sources", "no_dangling_cites")):
        ok, fails = score_citations(report, expect, source_count=source_count)
        details["citations"] = {"ok": ok, "failures": fails}
        if not ok:
            failures.extend(fails)

    if must_mention:
        ok, fails, hits = score_must_mention(report, must_mention)
        details["retrieval"] = {"ok": ok, "failures": fails, "hits": hits}
        if not ok:
            failures.extend(fails)

    return len(failures) == 0, failures, details


async def run_case(case: dict) -> dict:
    from gpt_researcher import GPTResearcher
    from gpt_researcher.utils.enum import ReportType, Tone

    case_id = case["id"]
    question = case["question"]
    report_source = case.get("report_source", "web")
    min_sources = int(case.get("min_sources", 0))
    report_language = case.get("report_language")

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
    elif report_source == "offline":
        # Offline fixture: score a canned report without calling the LLM
        report = case.get("offline_report") or ""
        sources = case.get("offline_sources") or []
        passed_base = True
        failures: list[str] = []
        if min_sources and len(sources) < min_sources:
            passed_base = False
            failures.append(f"expected min_sources>={min_sources}, got {len(sources)}")
        ok, score_fails, score_details = apply_scorers(report, case, len(sources))
        failures.extend(score_fails)
        return {
            "id": case_id,
            "report_source": report_source,
            "question": question,
            "passed": passed_base and ok,
            "failures": failures,
            "source_count": len(sources),
            "score_details": score_details,
            "offline": True,
        }
    else:
        raise ValueError(
            f"Case {case_id}: unsupported report_source '{report_source}'. "
            "Use 'web', 'hybrid', or 'offline'."
        )

    started = time.time()
    researcher_kwargs = dict(
        query=question,
        report_type=ReportType.ResearchReport.value,
        report_source=report_source,
        tone=Tone.Objective,
        verbose=True,
    )
    # report_language is applied via cfg/env when supported by caller kwargs
    if report_language:
        os.environ["REPORT_LANGUAGE"] = report_language

    researcher = GPTResearcher(**researcher_kwargs)
    await researcher.conduct_research()
    report = await researcher.write_report()
    elapsed = time.time() - started

    sources = researcher.get_source_urls()
    failures: list[str] = []
    passed = True

    if min_sources and len(sources) < min_sources:
        passed = False
        failures.append(f"expected min_sources>={min_sources}, got {len(sources)}")

    ok, score_fails, score_details = apply_scorers(report, case, len(sources))
    if not ok:
        passed = False
        failures.extend(score_fails)

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
        "score_details": score_details,
        "report_preview": report[:500],
    }


async def run_session_case() -> dict:
    from scorers.session import score_session_isolation

    ok, failures, meta = score_session_isolation()
    return {
        "id": "session-isolation-001",
        "report_source": "api",
        "passed": ok,
        "failures": failures,
        "meta": meta,
        "offline": meta.get("skipped", False),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="GPT Researcher harness (web + optional PDF)")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", type=str, default=None, help="Run a single case id")
    parser.add_argument(
        "--suite",
        choices=["cheap", "full", "nightly"],
        default="cheap",
        help="cheap=offline/deterministic; full/nightly=live research",
    )
    parser.add_argument(
        "--with-session",
        action="store_true",
        help="Also run API session isolation probe",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_cases(args.cases, args.only, args.limit, args.suite)
    if not cases and not args.with_session and args.suite != "cheap":
        print("No test cases to run.")
        return

    print(f"Running harness suite={args.suite} ({len(cases)} case(s))...")
    if args.suite == "nightly":
        print(
            "Nightly reminder: also run evals/simple_evals and evals/hallucination_eval "
            "for factuality/faithfulness baselines."
        )

    results = []
    for case in cases:
        print(f"\n--- {case['id']} ({case.get('report_source', 'web')}) ---")
        print(case.get("question", ""))
        try:
            result = await run_case(case)
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status} | sources={result.get('source_count')} | {result.get('elapsed_seconds', 0)}s")
            if result.get("failures"):
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

    if args.with_session or args.suite == "cheap":
        print("\n--- session-isolation-001 (api) ---")
        session_result = await run_session_case()
        status = "PASS" if session_result["passed"] else "FAIL"
        skipped = " (skipped/offline)" if session_result.get("offline") or session_result.get("meta", {}).get("skipped") else ""
        print(f"{status}{skipped}")
        results.append(session_result)

    ts = time.strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"run_{args.suite}_{ts}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    passed = sum(1 for r in results if r.get("passed"))
    print(f"\nSummary: {passed}/{len(results)} passed")
    print(f"Results: {out_path}")
    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
