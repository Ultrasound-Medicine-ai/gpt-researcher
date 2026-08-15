"""Offline fusion experiment on frozen final_v1 Gold; production retrieval is untouched."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from metrics import evidence_metrics, load_cases, raw_retrieval_metrics
from rag import context, retrieve
from rag.fts import fts_anchor_terms

ROOT = Path(__file__).parent
TENANT_ID = "rag-retrieval-corpus-v1"
USER_ID = "retrieval-eval"
RRF_K = 60


def grouped_split(cases: list[dict]) -> dict[str, str]:
    parent = {case["id"]: case["id"] for case in cases}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    by_parent: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        for parent_id in case["relevant_parent_ids"]:
            by_parent[parent_id].append(case["id"])
    for ids in by_parent.values():
        for case_id in ids[1:]:
            union(ids[0], case_id)
    groups: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        groups[find(case["id"])].append(case["id"])
    components = sorted(groups.values(), key=lambda ids: hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest())
    target = round(len(cases) * 0.25)
    choices: dict[int, tuple[int, ...]] = {0: ()}
    for index, component in enumerate(components):
        for count, selected in list(choices.items()):
            choices.setdefault(count + len(component), selected + (index,))
    holdout_groups = set(min(choices.items(), key=lambda item: (abs(item[0] - target), item[1]))[1])
    return {case_id: ("holdout" if index in holdout_groups else "main") for index, ids in enumerate(components) for case_id in ids}


def lexical_heavy(query: str) -> bool:
    return bool(re.search(r"\b[A-Z]{2,}\b|[a-z][A-Z]|(?:[A-Za-z]+-)+[A-Za-z]+|\d+(?:\.\d+)?%?", query))


def weighted_protected_fusion(fts: list[str], vector: list[str], *, fts_weight: float, fts_only_cap: int, gated: bool) -> list[str]:
    scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(vector, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    for rank, chunk_id in enumerate(fts, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + fts_weight / (RRF_K + rank)
    ranked = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], vector.index(chunk_id) if chunk_id in vector else 10_000, fts.index(chunk_id) if chunk_id in fts else 10_000))
    vector_set = set(vector)
    output: list[str] = []
    injected = 0
    cap = fts_only_cap if gated else 0
    for chunk_id in ranked:
        if chunk_id not in vector_set:
            if injected >= cap:
                continue
            injected += 1
        output.append(chunk_id)
    output.extend(chunk_id for chunk_id in vector if chunk_id not in output)
    return output


def calibrated_rrf(fts: list[str], vector: list[str], *, fts_weight: float) -> list[str]:
    """Calibrate unequal rank sources while retaining every candidate."""
    scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(vector, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    for rank, chunk_id in enumerate(fts, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + fts_weight / (RRF_K + rank)
    return sorted(
        scores,
        key=lambda chunk_id: (
            -scores[chunk_id],
            vector.index(chunk_id) if chunk_id in vector else 10_000,
            fts.index(chunk_id) if chunk_id in fts else 10_000,
        ),
    )


def agreement_weight(fts: list[str], vector: list[str], query: str) -> float:
    """Use retrieval agreement and concrete lexical anchors, not a classifier."""
    overlap = len(set(fts[:8]).intersection(vector[:8])) / 8
    anchor_strength = min(1.0, len(fts_anchor_terms(query)) / 2)
    return 0.50 + 0.25 * overlap + 0.25 * anchor_strength


def aggregate(items: list[dict]) -> dict[str, float]:
    keys = ("hit_at_5", "hit_at_8", "recall_at_5", "recall_at_8", "mrr_at_8", "parent_recall_at_8")
    return {key: round(sum(item[key] for item in items) / len(items), 6) for key in keys}


def main() -> None:
    cases = load_cases(ROOT / "retrieval_gold_final_40.jsonl")
    assert len(cases) == 40 and all(case["frozen"] and case["gold_version"] == "final_v1" for case in cases)
    split = grouped_split(cases)
    variants = {
        "pgvector_only": None,
        "equal_rrf": "equal",
        "calibrated_050_all": 0.50,
        "calibrated_075_all": 0.75,
        "agreement_calibrated_all": "agreement",
    }
    scores = {variant: {"main": [], "holdout": [], "all": []} for variant in variants}
    by_type = {variant: defaultdict(list) for variant in variants}
    rankings: dict[str, dict[str, list[str]]] = {}
    original_vector = retrieve.vector_search
    vector_cache: dict[tuple, list[str]] = {}

    def cached_vector(query: str, **kwargs) -> list[str]:
        key = (query, tuple(sorted(kwargs.items())))
        if key not in vector_cache:
            vector_cache[key] = original_vector(query, **kwargs)
        return vector_cache[key]

    retrieve.vector_search = cached_vector
    for case in cases:
        fts = retrieve.fts_search(case["query"], tenant_id=TENANT_ID, user_id=USER_ID, top_k=24)
        vector = retrieve.vector_search(case["query"], tenant_id=TENANT_ID, user_id=USER_ID, top_k=24)
        case_rankings = {}
        for variant, config in variants.items():
            if config is None:
                ranked = vector
            elif config == "equal":
                ranked = [chunk_id for chunk_id, _ in retrieve.rrf_fuse([fts, vector])]
            elif config == "agreement":
                ranked = calibrated_rrf(fts, vector, fts_weight=agreement_weight(fts, vector, case["query"]))
            else:
                ranked = calibrated_rrf(fts, vector, fts_weight=config)
            case_rankings[variant] = ranked
            parent_map = {chunk_id: chunk.parent_id or "" for chunk_id, chunk in retrieve.fetch_chunks_by_ids(ranked[:8]).items()}
            item = raw_retrieval_metrics(case["relevant_child_ids"], case["relevant_parent_ids"], ranked, parent_map)
            scores[variant][split[case["id"]]].append(item)
            scores[variant]["all"].append(item)
            by_type[variant][case["query_type"]].append(item)
        rankings[case["id"]] = case_rankings

    summaries = {variant: {partition: aggregate(items) for partition, items in partitions.items()} for variant, partitions in scores.items()}
    candidates = [variant for variant in variants if variant not in {"pgvector_only", "equal_rrf"}]
    selected = max(candidates, key=lambda variant: (summaries[variant]["main"]["recall_at_8"], summaries[variant]["main"]["hit_at_8"], summaries[variant]["main"]["mrr_at_8"]))

    evidence = {"main": [], "holdout": [], "all": []}
    for case in cases:
        ranked = rankings[case["id"]][selected]
        chunks_by_id = retrieve.fetch_chunks_by_ids(ranked)
        candidates_chunks = []
        for rank, chunk_id in enumerate(ranked):
            chunk = chunks_by_id.get(chunk_id)
            if chunk:
                chunk.retrieval_rank = rank
                candidates_chunks.append(chunk)
        primary, supplemental = retrieve.diversify_chunks(candidates_chunks, top_k=8, max_children_per_parent=2)
        hits = primary + supplemental
        siblings = retrieve._fetch_siblings(hits, tenant_id=TENANT_ID, user_id=USER_ID, session_id=None)
        neighbors = retrieve.expand_neighbors_from_siblings(hits, siblings, radius=1, excluded_ids={chunk.chunk_id for chunk in hits})
        packed = retrieve.pack_retrieval_candidates(primary, neighbors, supplemental, token_budget=3500)
        assembled = context.assemble_evidence(packed, token_budget=3500)
        item = evidence_metrics(case["relevant_child_ids"], [citation.chunk_id for citation in assembled.citations], context_token_count_estimated=assembled.total_tokens, token_budget=3500)
        evidence[split[case["id"]]].append(item["evidence_recall_at_3500"])
        evidence["all"].append(item["evidence_recall_at_3500"])

    result = {
        "benchmark": {"gold_version": "final_v1", "case_count": 40, "gold_modified": False},
        "split": {"method": "relevant_parent_connected_components", "counts": dict(Counter(split.values())), "query_types": {part: dict(Counter(case["query_type"] for case in cases if split[case["id"]] == part)) for part in ("main", "holdout")}},
        "variants": summaries,
        "selected_on_main": selected,
        "selected_evidence_recall_at_3500": {part: round(sum(values) / len(values), 6) for part, values in evidence.items()},
        "selected_recall_at_8_by_type_all": {kind: round(sum(item["recall_at_8"] for item in items) / len(items), 6) for kind, items in sorted(by_type[selected].items())},
        "holdout_validation": {
            "pgvector_recall_at_8": summaries["pgvector_only"]["holdout"]["recall_at_8"],
            "selected_recall_at_8": summaries[selected]["holdout"]["recall_at_8"],
            "delta": round(summaries[selected]["holdout"]["recall_at_8"] - summaries["pgvector_only"]["holdout"]["recall_at_8"], 6),
        },
    }
    (ROOT / "retrieval_rrf_calibration.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# FTS Fusion Experiment", "", "- Gold: frozen `final_v1`; no Gold, Query, retrieval parameter, or production code changes.", "- Selection uses Parent-grouped Main only; Holdout is read once for validation.", "", f"- Split: Main {result['split']['counts'].get('main', 0)} / Holdout {result['split']['counts'].get('holdout', 0)}", f"- Selected on Main: `{selected}`", "", "| Variant | Main Recall@8 | Holdout Recall@8 | All Recall@8 | All MRR@8 |", "|---|---:|---:|---:|---:|"]
    for variant in variants:
        lines.append(f"| {variant} | {summaries[variant]['main']['recall_at_8']:.4f} | {summaries[variant]['holdout']['recall_at_8']:.4f} | {summaries[variant]['all']['recall_at_8']:.4f} | {summaries[variant]['all']['mrr_at_8']:.4f} |")
    lines += ["", f"- Holdout delta vs PGVector: {result['holdout_validation']['delta']:+.4f}", f"- Selected Evidence Recall@3500 (all): {result['selected_evidence_recall_at_3500']['all']:.4f}"]
    (ROOT / "RRF_CALIBRATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"split": result["split"], "selected": selected, "holdout": result["holdout_validation"], "all": summaries[selected]["all"], "evidence": result["selected_evidence_recall_at_3500"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
