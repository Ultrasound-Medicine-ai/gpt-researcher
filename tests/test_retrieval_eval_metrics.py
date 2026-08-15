from __future__ import annotations

from pathlib import Path

import pytest

from evals.retrieval.metrics import evidence_metrics, load_cases, raw_retrieval_metrics


def test_raw_metrics_use_raw_child_ranking():
    metrics = raw_retrieval_metrics(
        ["gold-a", "gold-b"],
        ["parent-a", "parent-b"],
        ["miss", "gold-a", "other", "gold-b"],
        {
            "miss": "parent-x",
            "gold-a": "parent-a",
            "other": "parent-y",
            "gold-b": "parent-b",
        },
    )
    assert metrics == {
        "hit_at_5": 1.0,
        "hit_at_8": 1.0,
        "recall_at_5": 1.0,
        "recall_at_8": 1.0,
        "mrr_at_8": 0.5,
        "parent_recall_at_8": 1.0,
    }


def test_evidence_metrics_are_separate_and_budget_guarded():
    metrics = evidence_metrics(
        ["gold-a", "gold-b"],
        ["neighbor", "gold-b"],
        context_token_count_estimated=3499,
    )
    assert metrics["evidence_recall_at_3500"] == 0.5
    assert metrics["context_token_count_estimated"] == 3499
    with pytest.raises(ValueError):
        evidence_metrics(
            ["gold-a"], ["gold-a"], context_token_count_estimated=3501
        )


def test_candidate_gold_shape_and_split():
    path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "retrieval"
        / "retrieval_gold_candidates.jsonl"
    )
    cases = load_cases(path)
    assert len(cases) == 20
    assert sum(case["split"] == "main_candidate" for case in cases) == 15
    assert sum(case["split"] == "holdout_candidate" for case in cases) == 5
    assert {
        query_type: sum(case["query_type"] == query_type for case in cases)
        for query_type in {
            "exact_keyword",
            "semantic_paraphrase",
            "cross_chunk_boundary",
            "multi_section_synthesis",
        }
    } == {
        "exact_keyword": 5,
        "semantic_paraphrase": 5,
        "cross_chunk_boundary": 5,
        "multi_section_synthesis": 5,
    }
    assert all(case["candidate_status"] == "unreviewed_candidate" for case in cases)
    assert all(case["relevant_child_ids"] for case in cases)
    assert all(case["relevant_parent_ids"] for case in cases)
