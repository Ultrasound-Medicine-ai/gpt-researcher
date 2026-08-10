"""Deterministic eval sampling helpers. :-)"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "evals"))

from _common import resolve_sample_seed, seeded_sample  # noqa: E402


def test_seeded_sample_is_deterministic():
    pop = list(range(50))
    a = seeded_sample(pop, 5, seed=42)
    b = seeded_sample(pop, 5, seed=42)
    c = seeded_sample(pop, 5, seed=7)
    assert a == b
    assert a != c
    assert len(a) == 5


def test_resolve_sample_seed_cli_wins(monkeypatch):
    monkeypatch.setenv("EVAL_SAMPLE_SEED", "99")
    assert resolve_sample_seed(3) == 3
    assert resolve_sample_seed(None) == 99
    monkeypatch.delenv("EVAL_SAMPLE_SEED", raising=False)
    assert resolve_sample_seed(None) == 42
