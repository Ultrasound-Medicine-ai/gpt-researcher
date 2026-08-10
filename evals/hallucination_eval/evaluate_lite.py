"""Lightweight hallucination judge via ChatOpenAI (Matpool-friendly). :-)

Judges report faithfulness against a multi-source evidence pack (not a single
truncated snippet). Counts MAJOR unsupported claims only — minor embellishments
that do not change the reader's takeaway are ignored for the headline rate.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

PROMPT = """You are a faithfulness judge for a research report.

You are given an EVIDENCE PACK (multiple retrieved sources) and a REPORT.
Decide whether the REPORT contains MAJOR hallucinations relative to the pack.

MAJOR hallucination (mark YES):
- Invented paper titles, entities, organizations, or quotations not in the pack
- Numbers / dates / statistics that contradict the pack OR are specific quantitative
  claims with no grounding anywhere in the pack
- Clear false attribution (claiming source X said Y when pack does not support Y)

NOT major (mark NO) even if imperfect:
- Paraphrase / synthesis across multiple pack documents
- Reasonable qualitative elaboration without new hard facts
- Minor unit/translation wording issues when the magnitude matches the pack
- Structure, headings, citation markers
- Details that appear in a different pack document than the first one

Reply with exactly these lines first:
SEVERITY: MAJOR|MINOR|NONE
HALLUCINATION: YES|NO
Then a short reason (cite the unsupported claim if YES).
Use HALLUCINATION: YES only when SEVERITY is MAJOR.

EVIDENCE PACK:
{source}

REPORT:
{report}
"""


def _format_item(item: Any, index: int) -> str:
    if isinstance(item, dict):
        title = item.get("title") or item.get("name") or f"Source {index}"
        url = item.get("url") or item.get("href") or item.get("source") or ""
        body = (
            item.get("content")
            or item.get("raw_content")
            or item.get("text")
            or item.get("body")
            or ""
        )
        header = f"[DOC {index}] {title}"
        if url:
            header += f"\nURL: {url}"
        return f"{header}\n{body}".strip()
    text = str(item).strip()
    if not text:
        return ""
    if text.startswith(f"[DOC {index}]"):
        return text
    return f"[DOC {index}]\n{text}"


def _item_blob(item: Any) -> str:
    if isinstance(item, dict):
        parts = [
            str(item.get("url") or ""),
            str(item.get("title") or ""),
            str(item.get("content") or item.get("raw_content") or item.get("text") or ""),
        ]
        return "\n".join(parts).lower()
    return str(item).lower()


def _report_url_hosts(report: str) -> set[str]:
    hosts: set[str] = set()
    for match in re.findall(r"https?://[^\s\)\]\>\"']+", report or ""):
        try:
            host = urlparse(match).netloc.lower().removeprefix("www.")
            if host:
                hosts.add(host)
        except Exception:  # noqa: BLE001
            continue
    return hosts


def _normalize_items(context: Any) -> list[Any]:
    if context is None:
        return []
    if isinstance(context, str):
        split = re.split(r"\n{2,}(?=Source:|\[DOC )", context.strip())
        return [p.strip() for p in split if p.strip()] or ([context] if context.strip() else [])
    if isinstance(context, list):
        return list(context)
    return [context]


def pack_evidence_context(
    context: Any,
    *,
    report: str | None = None,
    max_chars: int = 36000,
    max_sources: int = 12,
    per_source_cap: int = 4500,
) -> str:
    """Join multi-source research context into a budgeted evidence pack. :-)"""
    items = _normalize_items(context)
    if not items:
        return ""

    # Prefer docs cited in the report so key evidence is not truncated away. :-)
    hosts = _report_url_hosts(report or "")
    if hosts:
        ranked: list[tuple[int, int, Any]] = []
        for i, item in enumerate(items):
            blob = _item_blob(item)
            hit = 1 if any(h in blob for h in hosts) else 0
            ranked.append((-hit, i, item))
        ranked.sort()
        items = [item for _, _, item in ranked]

    packed: list[str] = []
    used = 0
    for i, raw in enumerate(items[:max_sources], start=1):
        block = _format_item(raw, i)
        if not block:
            continue
        if len(block) > per_source_cap:
            block = block[: per_source_cap - 20].rstrip() + "\n...[truncated]"
        extra = 2 if packed else 0
        if packed and used + len(block) + extra > max_chars:
            break
        if not packed and len(block) > max_chars:
            block = block[: max_chars - 20].rstrip() + "\n...[truncated]"
        packed.append(block)
        used += len(block) + extra

    return "\n\n".join(packed)


def _strip_reference_tail(report: str) -> str:
    """Drop bibliography tail so judge focuses on body claims. :-)"""
    text = report or ""
    for marker in ("\n## 参考文献", "\n## References", "\n## sources", "\n## Sources"):
        idx = text.find(marker)
        if idx > 200:
            return text[:idx].rstrip()
    return text


class LiteHallucinationEvaluator:
    def __init__(self, grader_model: Any):
        self.grader_model = grader_model

    def evaluate_response(self, model_output: str, source_text: Any) -> dict:
        source = pack_evidence_context(source_text, report=model_output or "")
        report = _strip_reference_tail(model_output or "")[:10000]
        doc_count = len(re.findall(r"(?:^|\n)\[DOC \d+\]", source))
        if not source.strip():
            return {
                "output": model_output,
                "source": "",
                "source_pack_chars": 0,
                "source_doc_count": 0,
                "severity": None,
                "is_hallucination": None,
                "reasoning": "skipped — empty source",
            }
        msg = PROMPT.format(source=source, report=report)
        resp = self.grader_model.invoke([{"role": "user", "content": msg}])
        text = (getattr(resp, "content", None) or str(resp)).strip()

        sev_m = re.search(r"SEVERITY:\s*(MAJOR|MINOR|NONE)", text, re.IGNORECASE)
        severity = sev_m.group(1).upper() if sev_m else None
        yes = bool(re.search(r"HALLUCINATION:\s*YES", text, re.IGNORECASE))
        no = bool(re.search(r"HALLUCINATION:\s*NO", text, re.IGNORECASE))

        if severity == "MAJOR":
            is_hall: bool | None = True
        elif severity in {"MINOR", "NONE"}:
            is_hall = False
        else:
            is_hall = True if yes and not no else False if no else None

        return {
            "output": model_output,
            "source": source[:800],
            "source_pack_chars": len(source),
            "source_doc_count": doc_count or (1 if source else 0),
            "severity": severity,
            "is_hallucination": is_hall,
            "reasoning": text[:800],
        }
