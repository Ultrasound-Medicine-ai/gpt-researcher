"""Latency helpers for perf gates. :-)"""

from __future__ import annotations

import math
from typing import Sequence


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile (p in 0..100)."""
    if not values:
        return 0.0
    if p <= 0:
        return float(min(values))
    if p >= 100:
        return float(max(values))
    ordered = sorted(float(v) for v in values)
    # nearest-rank: ceil(p/100 * N) (1-indexed)
    rank = max(1, min(len(ordered), int(math.ceil(p / 100.0 * len(ordered)))))
    return ordered[rank - 1]


def p95(values: Sequence[float]) -> float:
    return percentile(values, 95.0)
