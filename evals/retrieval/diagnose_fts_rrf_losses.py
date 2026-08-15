"""Diagnose cases where equal RRF loses a pgvector Top-8 Gold hit."""

from __future__ import annotations

import json
from pathlib import Path

from rag.fts import fts_anchor_terms, fts_terms
from rag import retrieve

ROOT = Path(__file__).parent
TENANT_ID = "rag-retrieval-corpus-v1"
USER_ID = "retrieval-eval"


def _rank(ids: list[str], chunk_id: str) -> int | None:
    return ids.index(chunk_id) + 1 if chunk_id in ids else None


def main() -> None:
    cases = [json.loads(line) for line in (ROOT / "retrieval_gold_final_40.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    losses = []
    for case in cases:
        fts = retrieve.fts_search(case["query"], tenant_id=TENANT_ID, user_id=USER_ID, top_k=24)
        vector = retrieve.vector_search(case["query"], tenant_id=TENANT_ID, user_id=USER_ID, top_k=24)
        fused = [chunk_id for chunk_id, _ in retrieve.rrf_fuse([fts, vector])]
        lost_gold = [gold for gold in case["relevant_child_ids"] if gold in vector[:8] and gold not in fused[:8]]
        if not lost_gold:
            continue
        injected = [chunk_id for chunk_id in fused[:8] if chunk_id not in vector[:8]]
        chunks = retrieve.fetch_chunks_by_ids(lost_gold + injected)
        losses.append({
            "case_id": case["id"],
            "query_type": case["query_type"],
            "query": case["query"],
            "query_terms": fts_terms(case["query"]),
            "anchor_terms": fts_anchor_terms(case["query"]),
            "lost_gold": [{
                "child_id": child_id,
                "fts_rank": _rank(fts, child_id),
                "vector_rank": _rank(vector, child_id),
                "fused_rank": _rank(fused, child_id),
                "content": chunks[child_id].content[:500] if child_id in chunks else "",
            } for child_id in lost_gold],
            "fts_injected": [{
                "child_id": child_id,
                "fts_rank": _rank(fts, child_id),
                "vector_rank": _rank(vector, child_id),
                "fused_rank": _rank(fused, child_id),
                "content": chunks[child_id].content[:500] if child_id in chunks else "",
            } for child_id in injected],
        })
    path = ROOT / "fts_rrf_loss_diagnosis.json"
    path.write_text(json.dumps({"loss_case_count": len(losses), "cases": losses}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"loss_case_count": len(losses), "case_ids": [item["case_id"] for item in losses]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
