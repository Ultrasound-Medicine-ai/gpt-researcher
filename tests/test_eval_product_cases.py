"""Smoke tests for expanded product JSONL cases (schema + counts). :-)"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVALS = REPO / "evals"


def _load(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def test_product_jsonl_active_floor():
    """Portfolio claim: product regression JSONL should stay above ~50 active. :-)"""
    files = [
        EVALS / "dialogue_eval" / "cases.jsonl",
        EVALS / "dialogue_eval" / "live_cases.jsonl",
        EVALS / "tool_eval" / "cases.jsonl",
        EVALS / "memory_eval" / "cases.jsonl",
        EVALS / "fuzz_eval" / "cases.jsonl",
        EVALS / "perf_eval" / "cases.jsonl",
        EVALS / "harness_eval" / "test_cases.jsonl",
    ]
    active = 0
    blocked = 0
    for path in files:
        assert path.exists(), path
        for row in _load(path):
            status = (row.get("status") or "active").lower()
            if status == "blocked":
                blocked += 1
            else:
                active += 1
    assert active >= 50, f"active={active} blocked={blocked}"
    assert blocked >= 3


def test_cheap_cases_have_ids_and_expect():
    for rel in (
        "dialogue_eval/cases.jsonl",
        "tool_eval/cases.jsonl",
        "memory_eval/cases.jsonl",
        "fuzz_eval/cases.jsonl",
    ):
        path = EVALS / rel
        ids = set()
        for row in _load(path):
            assert row.get("id"), path
            assert row["id"] not in ids, row["id"]
            ids.add(row["id"])
            if (row.get("status") or "active").lower() == "active":
                assert "expect" in row, row["id"]
