"""Deterministic eval sampling helpers. :-)"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "evals"))

from _common import (  # noqa: E402
    resolve_sample_seed,
    seeded_sample,
    seeded_stratified_sample,
)
from hallucination_eval.query_buckets import risk_bucket, summarize_by_bucket  # noqa: E402


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


def test_seeded_stratified_sample_deterministic_and_quota():
    pop = [{"topic": "A", "i": i} for i in range(20)] + [
        {"topic": "B", "i": i} for i in range(30)
    ] + [{"topic": "C", "i": i} for i in range(50)]
    a, ca = seeded_stratified_sample(
        pop, 10, key_fn=lambda x: x["topic"], seed=42
    )
    b, cb = seeded_stratified_sample(
        pop, 10, key_fn=lambda x: x["topic"], seed=42
    )
    c, _ = seeded_stratified_sample(
        pop, 10, key_fn=lambda x: x["topic"], seed=7
    )
    assert a == b
    assert ca == cb
    assert a != c
    assert sum(ca.values()) == 10
    assert len(a) == 10
    # Proportional: C~5, B~3, A~2 (largest remainder). :-)
    assert ca.get("C", 0) >= ca.get("A", 0)
    assert set(Counter(x["topic"] for x in a).keys()) == set(ca.keys())


def test_stratified_differs_from_random():
    pop = [{"topic": t, "i": i} for t in ("A", "B", "C") for i in range(40)]
    stratified, counts = seeded_stratified_sample(
        pop, 30, key_fn=lambda x: x["topic"], seed=42
    )
    random_rows = seeded_sample(pop, 30, seed=42)
    assert [x["i"] for x in stratified] != [x["i"] for x in random_rows] or counts
    assert sum(counts.values()) == 30
    # All three topics present under stratified proportional draw. :-)
    assert len(counts) == 3


def test_risk_bucket_rules():
    assert risk_bucket("Compare pricing of vector DBs") == "pricing_compare"
    assert risk_bucket("Find live coverage of the 2025 NVIDIA GTC keynote") == "fresh_news"
    assert risk_bucket("Which companies are leading AI agents?") == "landscape_vendor"
    assert risk_bucket("Explain how RAG techniques work") == "howto_technical"
    assert risk_bucket("Hello world") == "other"


def test_summarize_by_bucket():
    rows = [
        {
            "input": "Compare pricing of X",
            "is_hallucination": True,
            "severity": "MAJOR",
            "risk_bucket": "pricing_compare",
        },
        {
            "input": "Compare pricing of Y",
            "is_hallucination": False,
            "severity": "NONE",
            "risk_bucket": "pricing_compare",
        },
        {
            "input": "Explain RAG",
            "is_hallucination": True,
            "severity": "MAJOR",
            "risk_bucket": "howto_technical",
        },
    ]
    by = summarize_by_bucket(rows)
    assert by["pricing_compare"]["n"] == 2
    assert by["pricing_compare"]["major"] == 1
    assert by["pricing_compare"]["major_rate"] == 0.5
    assert by["howto_technical"]["major"] == 1
