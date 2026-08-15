"""Minimal retrieval metrics; candidate labels must be reviewed before scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union


def load_cases(path: Union[str, Path]) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def raw_retrieval_metrics(
    relevant_child_ids: list[str],
    relevant_parent_ids: list[str],
    ranked_child_ids: list[str],
    parent_by_child: dict[str, str],
) -> dict[str, float]:
    relevant_children = set(relevant_child_ids)
    relevant_parents = set(relevant_parent_ids)

    def hit(k: int) -> float:
        return float(bool(relevant_children.intersection(ranked_child_ids[:k])))

    def recall(k: int) -> float:
        if not relevant_children:
            return 0.0
        return len(relevant_children.intersection(ranked_child_ids[:k])) / len(
            relevant_children
        )

    reciprocal_rank = 0.0
    for rank, child_id in enumerate(ranked_child_ids[:8], start=1):
        if child_id in relevant_children:
            reciprocal_rank = 1.0 / rank
            break
    retrieved_parents = {
        parent_by_child[child_id]
        for child_id in ranked_child_ids[:8]
        if child_id in parent_by_child
    }
    parent_recall = (
        len(relevant_parents.intersection(retrieved_parents)) / len(relevant_parents)
        if relevant_parents
        else 0.0
    )
    return {
        "hit_at_5": hit(5),
        "hit_at_8": hit(8),
        "recall_at_5": recall(5),
        "recall_at_8": recall(8),
        "mrr_at_8": reciprocal_rank,
        "parent_recall_at_8": parent_recall,
    }


def evidence_metrics(
    relevant_child_ids: list[str],
    evidence_child_ids: list[str],
    *,
    context_token_count_estimated: int,
    token_budget: int = 3500,
) -> dict[str, float | int]:
    if context_token_count_estimated > token_budget:
        raise ValueError("estimated context token budget exceeded")
    relevant = set(relevant_child_ids)
    recall = (
        len(relevant.intersection(evidence_child_ids)) / len(relevant)
        if relevant
        else 0.0
    )
    return {
        "evidence_recall_at_3500": recall,
        "context_token_count_estimated": context_token_count_estimated,
    }
