"""Run the fixed final_v1 retrieval ablation without changing retrieval settings."""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from metrics import evidence_metrics, load_cases, raw_retrieval_metrics

from rag import context, retrieve

ROOT = Path(__file__).parent
TENANT_ID = "rag-retrieval-corpus-v1"
USER_ID = "retrieval-eval"
OUTPUT_VERSION = os.getenv("RETRIEVAL_ABLATION_OUTPUT_VERSION", "v2")


def _mean(scores: list[dict]) -> dict[str, float]:
    keys = ("hit_at_5", "hit_at_8", "recall_at_5", "recall_at_8", "mrr_at_8", "parent_recall_at_8")
    return {key: round(sum(score[key] for score in scores) / len(scores), 6) for key in keys}


def _parent_map(ids: list[str]) -> dict[str, str]:
    return {chunk_id: chunk.parent_id or "" for chunk_id, chunk in retrieve.fetch_chunks_by_ids(ids).items()}


def main() -> None:
    cases = load_cases(ROOT / "retrieval_gold_final_40.jsonl")
    assert len(cases) == 40
    assert all(case.get("frozen") and case.get("gold_version") == "final_v1" and case.get("human_reviewed") for case in cases)

    original_vector_search = retrieve.vector_search
    vector_cache: dict[tuple, list[str]] = {}

    def cached_vector_search(query: str, **kwargs) -> list[str]:
        key = (query, tuple(sorted(kwargs.items())))
        if key not in vector_cache:
            vector_cache[key] = original_vector_search(query, **kwargs)
        return vector_cache[key]

    retrieve.vector_search = cached_vector_search
    scheme_scores: dict[str, list[dict]] = {name: [] for name in ("fts_only", "pgvector_only", "hybrid_rrf", "hybrid_rrf_context")}
    by_type: dict[str, dict[str, list[dict]]] = {name: defaultdict(list) for name in scheme_scores}
    evidence_scores: list[float] = []
    context_tokens: list[int] = []
    fts_nonempty = fts_gold_hits = vector_nonempty = 0
    sanity: dict[str, dict] = {}

    for case in cases:
        query = case["query"]
        fts = retrieve.fts_search(query, tenant_id=TENANT_ID, user_id=USER_ID, top_k=24)
        vector = retrieve.vector_search(query, tenant_id=TENANT_ID, user_id=USER_ID, top_k=24)
        fused = [
            chunk_id
            for chunk_id, _ in (
                retrieve.calibrated_rrf_fuse(fts, vector, query)
                if fts and vector
                else retrieve.rrf_fuse([part for part in (fts, vector) if part])
            )
        ]
        fts_nonempty += int(bool(fts))
        vector_nonempty += int(bool(vector))
        fts_gold_hits += int(bool(set(fts[:20]).intersection(case["relevant_child_ids"])))
        for name, ranked_ids in {"fts_only": fts, "pgvector_only": vector, "hybrid_rrf": fused, "hybrid_rrf_context": fused}.items():
            score = raw_retrieval_metrics(case["relevant_child_ids"], case["relevant_parent_ids"], ranked_ids, _parent_map(ranked_ids[:8]))
            scheme_scores[name].append(score)
            by_type[name][case["query_type"]].append(score)
        packed = retrieve.hybrid_retrieve(query, tenant_id=TENANT_ID, user_id=USER_ID, top_k=8)
        assembled = context.assemble_evidence(packed, token_budget=3500)
        evidence = evidence_metrics(case["relevant_child_ids"], [citation.chunk_id for citation in assembled.citations], context_token_count_estimated=assembled.total_tokens, token_budget=3500)
        evidence_scores.append(evidence["evidence_recall_at_3500"])
        context_tokens.append(evidence["context_token_count_estimated"])
        if case["id"] in {"candidate-021", "candidate-026", "candidate-031"}:
            sanity[case["id"]] = {"fts_top20_nonempty": bool(fts[:20]), "gold_ranks": {gold: (fts.index(gold) + 1 if gold in fts[:20] else None) for gold in case["relevant_child_ids"]}}

    schemes = {}
    per_type = {}
    for name, scores in scheme_scores.items():
        aggregate = _mean(scores)
        aggregate["evidence_recall_at_3500"] = round(sum(evidence_scores) / len(evidence_scores), 6) if name == "hybrid_rrf_context" else None
        aggregate["context_token_count_estimated_mean"] = round(sum(context_tokens) / len(context_tokens), 3) if name == "hybrid_rrf_context" else None
        schemes[name] = aggregate
        per_type[name] = {kind: round(sum(item["recall_at_8"] for item in values) / len(values), 6) for kind, values in sorted(by_type[name].items())}

    result = {
        "benchmark": {"case_count": 40, "gold_version": "final_v1", "frozen": True, "retriever_driven_gold_changes_prohibited": True},
        "fts": {"non_empty_rate": round(fts_nonempty / len(cases), 6), "top20_gold_hit_rate": round(fts_gold_hits / len(cases), 6)},
        "sanity": sanity,
        "schemes": schemes,
        "query_type_recall_at_8": per_type,
        "runtime": {"vector_nonempty_cases": vector_nonempty},
    }
    (ROOT / f"retrieval_ablation_final_{OUTPUT_VERSION}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    labels = {"fts_only": "A. FTS only", "pgvector_only": "B. pgvector only", "hybrid_rrf": "C. FTS + pgvector + calibrated RRF", "hybrid_rrf_context": "D. Calibrated Hybrid + Context"}
    lines = [f"# Retrieval Ablation - Final 40 Gold {OUTPUT_VERSION.upper()}", "", "- Frozen Gold: `final_v1`, 40 human-reviewed cases.", "- FTS uses jieba-segmented text stored in `content_tsv` and keyword-level OR tsquery.", "- Raw metrics use original Child rankings; Evidence Recall@3500 uses final packed Context only.", "", "## FTS health", "", f"- FTS non-empty rate: {result['fts']['non_empty_rate']:.4f}", f"- FTS Top20 Gold hit rate: {result['fts']['top20_gold_hit_rate']:.4f}", "", "## Aggregate metrics", "", "| Scheme | Hit@5 | Hit@8 | Recall@5 | Recall@8 | MRR@8 | Parent Recall@8 | Evidence Recall@3500 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, label in labels.items():
        item = schemes[name]
        evidence = "N/A" if item["evidence_recall_at_3500"] is None else f"{item['evidence_recall_at_3500']:.4f}"
        lines.append(f"| {label} | {item['hit_at_5']:.4f} | {item['hit_at_8']:.4f} | {item['recall_at_5']:.4f} | {item['recall_at_8']:.4f} | {item['mrr_at_8']:.4f} | {item['parent_recall_at_8']:.4f} | {evidence} |")
    lines += ["", "## Recall@8 by query type", "", "| Scheme | exact_keyword | semantic_paraphrase | cross_chunk_boundary | multi_parent_synthesis |", "|---|---:|---:|---:|---:|"]
    for name, label in labels.items():
        values = per_type[name]
        lines.append(f"| {label} | {values['exact_keyword']:.4f} | {values['semantic_paraphrase']:.4f} | {values['cross_chunk_boundary']:.4f} | {values['multi_parent_synthesis']:.4f} |")
    lines += ["", "## Three-case sanity", ""]
    for case_id, item in sanity.items():
        lines.append(f"- {case_id}: non-empty={item['fts_top20_nonempty']}, gold_ranks={item['gold_ranks']}")
    (ROOT / f"RETRIEVAL_ABLATION_FINAL_{OUTPUT_VERSION.upper()}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"fts": result["fts"], "sanity": sanity, "schemes": schemes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
