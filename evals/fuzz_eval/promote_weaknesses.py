"""Promote open fuzz weaknesses into active fuzz cases (systematic recycle). :-)

Usage:
  python evals/fuzz_eval/promote_weaknesses.py
  python evals/fuzz_eval/promote_weaknesses.py --limit 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases.jsonl"
WEAK = HERE / "weaknesses.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote fuzz weaknesses to cases")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cases = _load_jsonl(CASES)
    case_ids = {c.get("id") for c in cases}
    weaknesses = _load_jsonl(WEAK)
    open_rows = [w for w in weaknesses if (w.get("status") or "open") == "open"]

    promoted = 0
    new_cases: list[dict] = []
    for w in open_rows:
        if promoted >= args.limit:
            break
        wid = w.get("id") or f"fuzz-promoted-{promoted+1:03d}"
        # Always create a unique promoted id to avoid clobbering originals. :-)
        new_id = wid if wid not in case_ids else f"{wid}-promo-{promoted+1:02d}"
        if new_id in case_ids:
            continue
        expect = w.get("expect") or {
            "forbid_tools": ["create_research_report"],
            "no_tools": True,
        }
        case = {
            "id": new_id,
            "pillar": "fuzz",
            "suite": "cheap",
            "status": "active",
            "target": "chat",
            "user": w.get("user") or "",
            "expect": expect,
            "promoted_from": wid,
        }
        new_cases.append(case)
        case_ids.add(new_id)
        w["status"] = "promoted"
        w["promoted_case_id"] = new_id
        promoted += 1

    if args.dry_run:
        print(f"DRY-RUN would promote {promoted} weakness(es):")
        for c in new_cases:
            print(f"  + {c['id']}: {c.get('user')}")
        return

    if new_cases:
        _write_jsonl(CASES, cases + new_cases)
    _write_jsonl(WEAK, weaknesses)
    print(f"Promoted {promoted} weakness(es) into {CASES}")
    print(f"Updated {WEAK}")


if __name__ == "__main__":
    main()
