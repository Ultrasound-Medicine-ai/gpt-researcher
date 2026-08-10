"""Offline tests for perf P95 helper. :-)"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "perf_eval"))

from p95 import p95, percentile  # noqa: E402


def test_p95_basic():
    assert p95([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == 10.0
    assert percentile([10, 20, 30, 40], 50) == 20.0


def test_p95_empty():
    assert p95([]) == 0.0
