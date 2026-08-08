"""Language scorers for harness_eval (deterministic, no LLM)."""

from __future__ import annotations

import re


_CJK = re.compile(r"[\u4e00-\u9fff]")


def chinese_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    cjk = len(_CJK.findall(text))
    letters = sum(1 for ch in text if ch.isalpha() or _CJK.match(ch))
    if letters == 0:
        return 0.0
    return cjk / letters


def score_report_language(report: str, expect: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []
    lang = (expect.get("lang") or "").lower()
    refs_heading = expect.get("refs_heading")
    ratio = chinese_char_ratio(report)

    if lang in ("zh", "chinese"):
        min_ratio = float(expect.get("min_chinese_ratio", 0.15))
        if ratio < min_ratio:
            failures.append(f"chinese_ratio={ratio:.2f} < {min_ratio}")
    elif lang in ("en", "english"):
        max_ratio = float(expect.get("max_chinese_ratio", 0.35))
        if ratio > max_ratio:
            failures.append(f"chinese_ratio={ratio:.2f} > {max_ratio}")

    if refs_heading and refs_heading not in report:
        failures.append(f"missing refs heading: {refs_heading}")

    return len(failures) == 0, failures
