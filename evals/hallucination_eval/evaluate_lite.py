"""Lightweight hallucination judge via ChatOpenAI (Matpool-friendly). :-)"""

from __future__ import annotations

import re
from typing import Any

PROMPT = """You are a faithfulness judge for a research report.

Given SOURCE context and a REPORT, decide if the REPORT contains material claims
that are NOT supported by the SOURCE (hallucination).

Reply with exactly one line:
HALLUCINATION: YES
or
HALLUCINATION: NO
Then a short reason.

SOURCE:
{source}

REPORT:
{report}
"""


class LiteHallucinationEvaluator:
    def __init__(self, grader_model: Any):
        self.grader_model = grader_model

    def evaluate_response(self, model_output: str, source_text: str) -> dict:
        source = (source_text or "")[:12000]
        report = (model_output or "")[:8000]
        if not source.strip():
            return {
                "output": model_output,
                "source": "",
                "is_hallucination": None,
                "reasoning": "skipped — empty source",
            }
        msg = PROMPT.format(source=source, report=report)
        resp = self.grader_model.invoke([{"role": "user", "content": msg}])
        text = (getattr(resp, "content", None) or str(resp)).strip()
        yes = bool(re.search(r"HALLUCINATION:\s*YES", text, re.IGNORECASE))
        no = bool(re.search(r"HALLUCINATION:\s*NO", text, re.IGNORECASE))
        is_hall = True if yes and not no else False if no else None
        return {
            "output": model_output,
            "source": source[:500],
            "is_hallucination": is_hall,
            "reasoning": text[:800],
        }
