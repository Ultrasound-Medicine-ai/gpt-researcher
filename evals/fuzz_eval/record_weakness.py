"""Append fuzz failures into weaknesses.jsonl (deduped by id+user). :-)"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WEAK_PATH = Path(__file__).resolve().parent / "weaknesses.jsonl"


def _existing_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.is_file():
        return keys
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            keys.add(f"{row.get('id')}::{row.get('user')}")
    return keys


def record_weaknesses(results: list[dict[str, Any]], *, cases_by_id: dict[str, dict]) -> int:
    """Record failed fuzz cases. Returns number newly appended."""
    WEAK_PATH.parent.mkdir(parents=True, exist_ok=True)
    seen = _existing_keys(WEAK_PATH)
    added = 0
    with open(WEAK_PATH, "a", encoding="utf-8") as f:
        for row in results:
            if row.get("skipped") or row.get("passed") is not False:
                continue
            case_id = str(row.get("id") or "")
            case = cases_by_id.get(case_id) or {}
            user = str(case.get("user") or row.get("user") or "")
            key = f"{case_id}::{user}"
            if key in seen:
                continue
            payload = {
                "id": case_id,
                "user": user,
                "expect": case.get("expect") or {},
                "failures": row.get("failures") or [],
                "intent_action": row.get("intent_action"),
                "tools": row.get("tools") or [],
                "status": "open",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            seen.add(key)
            added += 1
    return added
