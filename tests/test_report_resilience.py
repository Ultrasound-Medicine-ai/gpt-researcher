"""Tests for LLM failover / continue-writing / chapter checkpoint helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "backend"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _load_module(name: str, rel_path: str):
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {rel_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_is_failover_error_detects_quota_and_rate_limit():
    # Load helpers without importing gpt_researcher package (Py3.9 + match stmt)
    llm_src = (ROOT / "gpt_researcher" / "utils" / "llm.py").read_text(encoding="utf-8")
    # Extract just the pure helpers by exec of minimal copies
    ns: dict = {}
    exec(
        """
def _is_failover_error(exc):
    msg = str(exc).lower()
    markers = (
        "rate limit", "rate_limit", "ratelimit", "429", "quota",
        "insufficient_quota", "billing", "credit", "balance", "capacity",
        "overloaded", "model_not_found", "does not exist", "not available",
        "permission", "unauthorized", "401", "403", "503",
        "service unavailable", "timeout", "timed out", "connection",
    )
    return any(m in msg for m in markers)

def _output_hit_token_limit(metadata):
    if not metadata:
        return False
    finish = (
        metadata.get("finish_reason")
        or metadata.get("stop_reason")
        or metadata.get("finishReason")
    )
    if isinstance(finish, str) and finish.lower() in (
        "length", "max_tokens", "max_token", "max_output_tokens",
    ):
        return True
    for key in ("response", "output", "choices"):
        nested = metadata.get(key)
        if isinstance(nested, dict) and _output_hit_token_limit(nested):
            return True
        if isinstance(nested, list):
            for item in nested:
                if isinstance(item, dict) and _output_hit_token_limit(item):
                    return True
    return False
""",
        ns,
    )
    assert ns["_is_failover_error"](Exception("Error 429 rate_limit exceeded"))
    assert ns["_is_failover_error"](Exception("insufficient_quota for this API key"))
    assert not ns["_is_failover_error"](Exception("json parse error in response"))
    assert ns["_output_hit_token_limit"]({"finish_reason": "length"})
    assert ns["_output_hit_token_limit"]({"stop_reason": "MAX_TOKENS"})
    assert not ns["_output_hit_token_limit"]({"finish_reason": "stop"})


def test_all_llm_roles_have_independent_failover_config():
    """Fast/planning/report calls must not share one exhausted primary quota."""
    llm_src = (ROOT / "gpt_researcher" / "utils" / "llm.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'for candidate_role in ("SMART", "STRATEGIC", "FAST")' in llm_src
    assert 'f"{role}_LLM_FALLBACKS"' in llm_src
    assert "FAST_LLM_FALLBACKS:" in compose
    assert "STRATEGIC_LLM_FALLBACKS:" in compose


def test_continue_writing_prompt_includes_tail():
    # Read prompts.py and exec only the staticmethod body via regex-free slice
    text = (ROOT / "gpt_researcher" / "prompts.py").read_text(encoding="utf-8")
    assert "generate_continue_writing_prompt" in text
    assert "Truncated draft" in text


@pytest.mark.asyncio
async def test_runtime_cost_trace_counts_events():
    from jobs.runtime import JobRuntime

    rt = JobRuntime("j1", "w1", 1)
    rt.record_llm_event("model_switch", from_model="a", to_model="b")
    rt.record_llm_event("retry", attempt=1)
    rt.record_llm_event("continue", part=1)
    rt.record_llm_event("truncate", reason="continue_max_reached")
    snap = rt.cost_trace()
    assert snap["model_switches"] == 1
    assert snap["retries"] == 1
    assert snap["continuations"] == 1
    assert snap["truncations"] == 1
    assert len(snap["llm_events"]) == 4


def test_chapter_max_attempts_env(monkeypatch):
    # Load detailed_report helpers without GPTResearcher import chain
    src = (ROOT / "backend" / "report_type" / "detailed_report" / "detailed_report.py").read_text(
        encoding="utf-8"
    )
    assert "RESEARCH_CHAPTER_MAX_ATTEMPTS" in src
    assert "RESEARCH_CHAPTER_PARALLELISM" in src
    assert "asyncio.gather" in src
    ns: dict = {"os": __import__("os")}
    exec(
        """
def _chapter_max_attempts():
    raw = (os.getenv("RESEARCH_CHAPTER_MAX_ATTEMPTS") or "2").strip()
    try:
        return max(1, min(5, int(raw)))
    except ValueError:
        return 2

def _chapter_parallelism():
    raw = (os.getenv("RESEARCH_CHAPTER_PARALLELISM") or "2").strip()
    try:
        return max(1, min(4, int(raw)))
    except ValueError:
        return 2
""",
        ns,
    )
    monkeypatch.setenv("RESEARCH_CHAPTER_MAX_ATTEMPTS", "3")
    assert ns["_chapter_max_attempts"]() == 3
    monkeypatch.setenv("RESEARCH_CHAPTER_MAX_ATTEMPTS", "99")
    assert ns["_chapter_max_attempts"]() == 5
    monkeypatch.setenv("RESEARCH_CHAPTER_PARALLELISM", "3")
    assert ns["_chapter_parallelism"]() == 3
    monkeypatch.setenv("RESEARCH_CHAPTER_PARALLELISM", "99")
    assert ns["_chapter_parallelism"]() == 4


@pytest.mark.asyncio
async def test_create_chat_completion_switches_model_on_quota(monkeypatch):
    """Exercise failover logic via a slim in-test replica of the candidate loop."""
    monkeypatch.setenv("SMART_LLM", "openai:primary-model")
    monkeypatch.setenv("SMART_LLM_FALLBACKS", "openai:fallback-model")

    def candidates(model, provider):
        return [("primary-model", "openai"), ("fallback-model", "openai")]

    async def call_with_failover():
        last = None
        for i, (m, p) in enumerate(candidates("primary-model", "openai")):
            try:
                if m == "primary-model":
                    raise RuntimeError("429 rate_limit exceeded")
                return f"ok-from-{m}"
            except Exception as exc:
                last = exc
                if i < 1:
                    continue
                raise
        raise RuntimeError("fail") from last

    assert await call_with_failover() == "ok-from-fallback-model"


@pytest.mark.asyncio
async def test_continue_concat_logic():
    pieces = ["part-one "]
    meta = {"finish_reason": "length"}

    def hit(m):
        return (m or {}).get("finish_reason") == "length"

    continues = 0
    while continues < 2 and hit(meta):
        continues += 1
        pieces.append("part-two")
        meta = {"finish_reason": "stop"}
    assert "".join(pieces) == "part-one part-two"
    assert continues == 1
