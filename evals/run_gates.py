"""Unified Project-2 gate runner: cheap | full | nightly. :-)"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS = Path(__file__).resolve().parent
RESULTS = EVALS / "results"


def _run(cmd: list[str], *, cwd: Path | None = None) -> dict:
    started = time.time()
    print(f"\n>> {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        text=True,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "elapsed_sec": round(time.time() - started, 2),
        "ok": proc.returncode == 0,
    }


def run_cheap() -> list[dict]:
    steps: list[dict] = []
    steps.append(
        _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_harness_scorers.py",
                "tests/test_deterministic_cite.py",
                "tests/test_citation_registry.py",
                "tests/test_report_language.py",
                "tests/test_planning_context.py",
                "tests/test_eval_sample_seed.py",
                "-q",
            ]
        )
    )
    steps.append(
        _run([sys.executable, "evals/harness_eval/run_eval.py", "--suite", "cheap"])
    )
    steps.append(
        _run([sys.executable, "evals/dialogue_eval/run_eval.py", "--suite", "cheap"])
    )
    steps.append(
        _run([sys.executable, "evals/tool_eval/run_eval.py", "--suite", "cheap"])
    )
    steps.append(
        _run([sys.executable, "evals/memory_eval/run_eval.py", "--suite", "cheap"])
    )
    steps.append(
        _run([sys.executable, "evals/fuzz_eval/run_eval.py", "--suite", "cheap"])
    )
    return steps


def run_full(limit: int, *, live_chat: bool = True, base_url: str = "http://127.0.0.1:8000") -> list[dict]:
    steps: list[dict] = []
    steps.append(
        _run(
            [
                sys.executable,
                "evals/harness_eval/run_eval.py",
                "--suite",
                "full",
                "--limit",
                str(limit),
            ]
        )
    )
    import os

    enabled = live_chat or (os.getenv("EVAL_LIVE_CHAT") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    # Default ON for full suite; set EVAL_LIVE_CHAT=0 to skip. :-)
    disabled = (os.getenv("EVAL_LIVE_CHAT") or "").strip().lower() in {"0", "false", "no"}
    if enabled and not disabled:
        steps.append(
            _run(
                [
                    sys.executable,
                    "evals/dialogue_eval/run_live.py",
                    "--base-url",
                    base_url,
                    "--limit",
                    "3",
                ]
            )
        )
    return steps


def run_nightly(num_examples: int, seed: int | None = None) -> list[dict]:
    steps: list[dict] = []
    # Skip harness nightly alias noise; focus on quality baselines.
    simpleqa_cmd = [
        sys.executable,
        "evals/simple_evals/run_eval.py",
        "--num_examples",
        str(num_examples),
    ]
    hall_cmd = [
        sys.executable,
        "evals/hallucination_eval/run_eval.py",
        "-n",
        str(num_examples),
        "--judge",
        "lite",
    ]
    if seed is not None:
        simpleqa_cmd.extend(["--seed", str(seed)])
        hall_cmd.extend(["--seed", str(seed)])
    steps.append(_run(simpleqa_cmd))
    steps.append(_run(hall_cmd))
    return steps


def write_summary(suite: str, steps: list[dict]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS / f"gate_{suite}_{ts}.json"
    payload = {
        "suite": suite,
        "timestamp": ts,
        "ok": all(s.get("ok") for s in steps),
        "steps": steps,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = RESULTS / f"gate_{suite}_latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def main() -> None:
    if sys.version_info < (3, 10):
        print(
            "ERROR: Project-2 gates require Python >= 3.10 "
            f"(current {sys.version.split()[0]}).\n"
            "Use the project env, e.g.\n"
            "  D:\\anaconda3\\envs\\gptresearcher\\python.exe evals/run_gates.py --suite cheap",
            file=sys.stderr,
        )
        raise SystemExit(2)

    parser = argparse.ArgumentParser(description="Project-2 unified eval gates")
    parser.add_argument(
        "--suite",
        required=True,
        choices=["cheap", "full", "nightly"],
        help="Gate layer to run",
    )
    parser.add_argument("--limit", type=int, default=2, help="full suite case limit")
    parser.add_argument(
        "--num-examples",
        type=int,
        default=1,
        help="nightly SimpleQA / hallucination sample size",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Sample seed for nightly (default: EVAL_SAMPLE_SEED or 42)",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base for live chat in full suite",
    )
    args = parser.parse_args()

    if args.suite == "cheap":
        steps = run_cheap()
    elif args.suite == "full":
        steps = run_full(args.limit, base_url=args.base_url)
    else:
        steps = run_nightly(args.num_examples, seed=args.seed)

    out = write_summary(args.suite, steps)
    failed = [s for s in steps if not s.get("ok")]
    print("\n=== Gate summary ===")
    for s in steps:
        mark = "OK" if s.get("ok") else "FAIL"
        cmd = " ".join(str(x) for x in (s.get("cmd") or []))
        print(f"  {mark} ({s.get('elapsed_sec')}s) {cmd}")
    print(f"Wrote {out}")
    if failed:
        raise SystemExit(1)
    print(f"SUITE {args.suite} PASSED")


if __name__ == "__main__":
    main()
