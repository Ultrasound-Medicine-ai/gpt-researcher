"""Citation scorers for harness_eval (deterministic)."""

from __future__ import annotations

import re

_CITE = re.compile(r"\[(\d+)\]")


def extract_inline_citations(report: str) -> set[int]:
    body = report
    for marker in ("\n## 参考文献", "\n## References"):
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]
            break
    return {int(n) for n in _CITE.findall(body)}


def extract_reference_numbers(report: str) -> set[int]:
    refs = ""
    for marker in ("\n## 参考文献", "\n## References"):
        idx = report.find(marker)
        if idx >= 0:
            refs = report[idx:]
            break
    if not refs:
        return set()
    nums: set[int] = set()
    for m in re.finditer(r"\*\*\[(\d+)\]\*\*", refs):
        nums.add(int(m.group(1)))
    if not nums:
        for m in re.finditer(r"\[(\d+)\]", refs):
            nums.add(int(m.group(1)))
    return nums


def score_citations(report: str, expect: dict, source_count: int = 0) -> tuple[bool, list[str]]:
    failures: list[str] = []
    cites = extract_inline_citations(report)
    refs = extract_reference_numbers(report)

    min_cites = int(expect.get("min_bracket_cites", 0) or 0)
    if min_cites and len(cites) < min_cites:
        failures.append(f"min_bracket_cites: got {len(cites)} < {min_cites}")

    if expect.get("cites_subseteq_sources") or expect.get("no_dangling_cites"):
        if refs and cites - refs:
            failures.append(f"dangling cites not in refs: {sorted(cites - refs)}")
        elif source_count and cites:
            invalid = {n for n in cites if n < 1 or n > source_count}
            if invalid:
                failures.append(f"invalid citation numbers: {sorted(invalid)}")

    return len(failures) == 0, failures
