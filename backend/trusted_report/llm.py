"""Thin LLM JSON helper for trusted report stages."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty LLM response")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK.search(text)
    if not match:
        raise ValueError("no JSON object in LLM response")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be object")
    return data


async def call_llm_json(
    *,
    system: str,
    user: str,
    llm_call: Optional[Callable[..., Any]] = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Call chat completion and parse JSON.

    llm_call is injectable for tests: async (messages) -> str
    """
    if llm_call is not None:
        content = await llm_call(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        return extract_json_object(content if isinstance(content, str) else str(content))

    from gpt_researcher.utils.llm import create_chat_completion
    from gpt_researcher.config.config import Config

    cfg = Config()
    try:
        from jobs.runtime import JobRuntime

        rt = JobRuntime.current()
        if rt is not None:
            await rt.register_llm_call("trusted_report")
    except Exception:
        pass

    raw = await create_chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=cfg.smart_llm_model,
        llm_provider=cfg.smart_llm_provider,
        temperature=temperature,
        llm_kwargs=cfg.llm_kwargs,
        cost_callback=None,
    )
    return extract_json_object(raw or "")
