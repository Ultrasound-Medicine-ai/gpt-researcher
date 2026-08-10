"""Nightly orchestration helper (thin wrapper around run_gates). :-)

Usage:
    python evals/run_nightly.py --num-examples 5
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Project-2 nightly gate wrapper")
    parser.add_argument("--num-examples", type=int, default=5)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Sample seed (default: EVAL_SAMPLE_SEED or 42)",
    )
    args = parser.parse_args()
    cmd = [
        sys.executable,
        str(REPO_ROOT / "evals" / "run_gates.py"),
        "--suite",
        "nightly",
        "--num-examples",
        str(args.num_examples),
    ]
    if args.seed is not None:
        cmd.extend(["--seed", str(args.seed)])
    print(">>", " ".join(cmd))
    raise SystemExit(subprocess.call(cmd, cwd=str(REPO_ROOT)))


if __name__ == "__main__":
    main()
