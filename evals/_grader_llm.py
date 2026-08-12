"""Build a ChatOpenAI-compatible grader; fall back to GPTR create_chat_completion. :-)"""

from __future__ import annotations

import asyncio
import os
from typing import Any


def ensure_openai_compatible_env() -> None:
    """Map MATPOOL_* into OPENAI_* so langchain_openai works when possible."""
    if not (os.getenv("OPENAI_API_KEY") or "").strip():
        mp = (os.getenv("MATPOOL_API_KEY") or "").strip()
        if mp:
            os.environ["OPENAI_API_KEY"] = mp
    if not (os.getenv("OPENAI_BASE_URL") or "").strip():
        base = (os.getenv("MATPOOL_BASE_URL") or "").strip()
        if base:
            os.environ["OPENAI_BASE_URL"] = base.rstrip("/")


class _GPTRGrader:
    """Sync `.invoke(messages)` facade over async create_chat_completion."""

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model

    def invoke(self, messages: list[dict], **_kwargs: Any) -> Any:
        from gpt_researcher.utils.llm import create_chat_completion

        async def _run() -> str:
            return await create_chat_completion(
                messages=messages,
                model=self.model,
                llm_provider=self.provider,
                temperature=0,
                # The judge contract needs two labels plus a short reason;
                # keeping the completion bounded avoids provider timeouts while
                # leaving the evidence and scoring rubric unchanged.
                max_tokens=250,
            )

        def _run_sync() -> str:
            return asyncio.run(_run())

        try:
            asyncio.get_running_loop()
            in_loop = True
        except RuntimeError:
            in_loop = False

        if in_loop:
            # grade_response is sync but often called from async eval runners. :-)
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                content = pool.submit(_run_sync).result(timeout=180)
        else:
            content = _run_sync()

        class _Resp:
            def __init__(self, text: str):
                self.content = text

        return _Resp(content or "")


def build_grader_chat_model(**overrides: Any):
    """
    Prefer project SMART/FAST LLM (same keys as research).
    Override with EVAL_GRADER_LLM=provider:model
    """
    raw = (
        overrides.pop("model_name", None)
        or os.getenv("EVAL_GRADER_LLM")
        or os.getenv("FAST_LLM")
        or os.getenv("SMART_LLM")
        or ""
    ).strip()
    if raw and ":" in raw:
        provider, model = raw.split(":", 1)
        return _GPTRGrader(provider.strip(), model.strip())

    # Fallback: langchain ChatOpenAI via Matpool/OpenAI env
    ensure_openai_compatible_env()
    from langchain_openai import ChatOpenAI

    model = raw or os.getenv("EVAL_GRADER_MODEL") or "Qwen-Plus"
    if ":" in model:
        model = model.split(":", 1)[1]
    kwargs: dict[str, Any] = {
        "temperature": 0,
        "model": model,
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
    }
    base = (os.getenv("OPENAI_BASE_URL") or "").strip()
    if base:
        kwargs["openai_api_base"] = base.rstrip("/")
    kwargs.update(overrides)
    return ChatOpenAI(**kwargs)
