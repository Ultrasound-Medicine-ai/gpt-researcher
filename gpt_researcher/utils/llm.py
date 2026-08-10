"""LLM utilities for GPT Researcher.

This module provides utility functions for interacting with various
LLM providers through a unified interface.
"""
from __future__ import annotations

import logging
import os
from typing import Any
import asyncio

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from gpt_researcher.llm_provider.generic.base import (
    NO_SUPPORT_TEMPERATURE_MODELS,
    SUPPORT_REASONING_EFFORT_MODELS,
    ReasoningEfforts,
)

from ..prompts import PromptFamily
from .costs import calculate_llm_cost
from .validators import Subtopics

logger = logging.getLogger(__name__)


def get_llm(llm_provider: str, **kwargs):
    """Get an LLM provider instance.

    Args:
        llm_provider: The name of the LLM provider (e.g., 'openai', 'anthropic').
        **kwargs: Additional keyword arguments passed to the provider.

    Returns:
        A GenericLLMProvider instance configured for the specified provider.
    """
    from gpt_researcher.llm_provider import GenericLLMProvider
    return GenericLLMProvider.from_provider(llm_provider, **kwargs)


def _llm_candidates(model: str, llm_provider: str | None) -> list[tuple[str, str | None]]:
    """Return the configured role's primary model followed by its failovers.

    FAST, SMART and STRATEGIC workloads use independent fallback chains, so a
    planning-model quota failure does not take down report writing. Entries use
    ``provider:model`` in ``<ROLE>_LLM_FALLBACKS``.
    """
    role = None
    for candidate_role in ("SMART", "STRATEGIC", "FAST"):
        primary = os.getenv(f"{candidate_role}_LLM", "")
        try:
            primary_provider, primary_model = primary.split(":", 1)
        except ValueError:
            continue
        if (model, llm_provider) == (primary_model, primary_provider):
            role = candidate_role
            break

    if role is None:
        return [(model, llm_provider)]

    candidates: list[tuple[str, str | None]] = [(model, llm_provider)]
    for entry in os.getenv(f"{role}_LLM_FALLBACKS", "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            provider, fallback_model = entry.split(":", 1)
        except ValueError:
            logger.warning(
                "Ignoring invalid %s_LLM_FALLBACKS entry; expected provider:model",
                role,
            )
            continue
        candidate = (fallback_model, provider)
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _smart_llm_candidates(model: str, llm_provider: str | None) -> list[tuple[str, str | None]]:
    """Backward-compatible alias for older callers/tests."""
    return _llm_candidates(model, llm_provider)


def _is_failover_error(exc: BaseException) -> bool:
    """True when the failure is likely model/quota/rate-limit (try next model)."""
    msg = str(exc).lower()
    markers = (
        "rate limit",
        "rate_limit",
        "ratelimit",
        "429",
        "quota",
        "insufficient_quota",
        "billing",
        "credit",
        "balance",
        "capacity",
        "overloaded",
        "model_not_found",
        "does not exist",
        "not available",
        "permission",
        "unauthorized",
        "401",
        "403",
        "503",
        "service unavailable",
        "timeout",
        "timed out",
        "connection",
    )
    return any(m in msg for m in markers)


def _output_hit_token_limit(metadata: dict[str, Any] | None) -> bool:
    if not metadata:
        return False
    finish = (
        metadata.get("finish_reason")
        or metadata.get("stop_reason")
        or metadata.get("finishReason")
    )
    if isinstance(finish, str) and finish.lower() in (
        "length",
        "max_tokens",
        "max_token",
        "max_output_tokens",
    ):
        return True
    # Nested provider shapes
    for key in ("response", "output", "choices"):
        nested = metadata.get(key)
        if isinstance(nested, dict) and _output_hit_token_limit(nested):
            return True
        if isinstance(nested, list):
            for item in nested:
                if isinstance(item, dict) and _output_hit_token_limit(item):
                    return True
    return False


def _record_runtime_event(event_type: str, **fields: Any) -> None:
    try:
        from jobs.runtime import get_abort_runtime

        runtime = get_abort_runtime()
        if runtime is not None:
            runtime.record_llm_event(event_type, **fields)
    except ImportError:
        pass


async def _persist_runtime_trace() -> None:
    try:
        from jobs.runtime import get_abort_runtime

        runtime = get_abort_runtime()
        if runtime is not None:
            await runtime.save_checkpoint()
    except Exception:
        pass


def _continue_max() -> int:
    raw = (os.getenv("RESEARCH_LLM_CONTINUE_MAX") or "2").strip()
    try:
        return max(0, min(5, int(raw)))
    except ValueError:
        return 2


def _continue_messages(
    messages: list[dict[str, str]],
    partial: str,
) -> list[dict[str, str]]:
    """Build messages that ask the model to resume from a truncated draft."""
    from ..prompts import PromptFamily

    tail = partial[-2500:] if len(partial) > 2500 else partial
    cont = PromptFamily.generate_continue_writing_prompt(tail)
    # Keep system + original user, then assistant partial + continue user
    out = list(messages)
    out.append({"role": "assistant", "content": partial})
    out.append({"role": "user", "content": cont})
    return out


async def create_chat_completion(
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = 0.4,
        max_tokens: int | None = 4000,
        llm_provider: str | None = None,
        stream: bool = False,
        websocket: Any | None = None,
        llm_kwargs: dict[str, Any] | None = None,
        cost_callback: callable = None,
        reasoning_effort: str | None = ReasoningEfforts.Medium.value,
        allow_continue: bool = True,
        **kwargs
) -> str:
    """Create a chat completion using the OpenAI API
    Args:
        messages (list[dict[str, str]]): The messages to send to the chat completion.
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.4.
        max_tokens (int, optional): The max tokens to use. Defaults to 4000.
        llm_provider (str, optional): The LLM Provider to use.
        stream (bool): Whether to stream the response. Defaults to False.
        webocket (WebSocket): The websocket used in the currect request,
        llm_kwargs (dict[str, Any], optional): Additional LLM keyword arguments. Defaults to None.
        cost_callback: Callback function for updating cost.
        reasoning_effort (str, optional): Reasoning effort for OpenAI's reasoning models. Defaults to 'low'.
        allow_continue: When True, resume writing if finish_reason indicates length.
        **kwargs: Additional keyword arguments.
    Returns:
        str: The response from the chat completion.
    """
    # validate input
    if model is None:
        raise ValueError("Model cannot be None")
    # Sanity guard against absurd values (e.g., env var typos). The actual
    # per-model output limits are enforced by the upstream provider.
    if max_tokens is not None and max_tokens > 200_000:
        raise ValueError(
            f"max_tokens={max_tokens} exceeds the largest output limit of "
            "any currently available model (128k as of late 2025). "
            "Check your FAST_TOKEN_LIMIT / SMART_TOKEN_LIMIT / "
            "STRATEGIC_TOKEN_LIMIT env vars for typos."
        )

    # Stop before spending another model call when job was cancelled / budget hit
    try:
        from jobs.runtime import check_abort, get_abort_runtime

        await check_abort(where="pre_llm")
        runtime = get_abort_runtime()
        if runtime is not None:
            runtime.register_llm_call(where="create_chat_completion")
    except ImportError:
        pass

    candidates = _llm_candidates(model, llm_provider)
    # A quota error is not improved by retrying the same model. Two attempts
    # still cover brief provider/network failures before failover.
    max_attempts = 1 if (stream and websocket is not None) else 2
    last_exception: Exception | None = None
    for candidate_index, (candidate_model, candidate_provider) in enumerate(candidates):
        try:
            from jobs.runtime import check_abort

            await check_abort(where=f"llm_candidate_{candidate_model}")
        except ImportError:
            pass
        provider_kwargs = {'model': candidate_model}
        if llm_kwargs:
            provider_kwargs.update(llm_kwargs)
        if candidate_model in SUPPORT_REASONING_EFFORT_MODELS:
            provider_kwargs['reasoning_effort'] = reasoning_effort
        if candidate_model not in NO_SUPPORT_TEMPERATURE_MODELS:
            provider_kwargs['temperature'] = temperature
            provider_kwargs['max_tokens'] = max_tokens
        else:
            provider_kwargs['temperature'] = None
            provider_kwargs['max_tokens'] = None
        if candidate_provider == "openai":
            base_url = os.environ.get("OPENAI_BASE_URL", None)
            if base_url:
                provider_kwargs['openai_api_base'] = base_url

        provider = get_llm(candidate_provider, **provider_kwargs)
        for attempt in range(1, max_attempts + 1):
            try:
                from jobs.runtime import check_abort

                await check_abort(where=f"llm_retry_{attempt}")
            except ImportError:
                pass
            try:
                response = await provider.get_chat_response(messages, stream, websocket, **kwargs)
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "LLM request failed for %s (attempt %s/%s): %s",
                    candidate_model, attempt, max_attempts, exc,
                )
                _record_runtime_event(
                    "retry",
                    model=candidate_model,
                    provider=candidate_provider,
                    attempt=attempt,
                    error=str(exc)[:300],
                    failover_worthy=_is_failover_error(exc),
                )
                if attempt < max_attempts and not _is_failover_error(exc):
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue
                # Quota / rate-limit → leave attempt loop and try next model
                if _is_failover_error(exc):
                    break
                if attempt < max_attempts:
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue
                break

            if not response:
                last_exception = RuntimeError("Empty response from LLM provider")
                logger.warning(
                    "LLM returned an empty response from %s (attempt %s/%s)",
                    candidate_model, attempt, max_attempts,
                )
                _record_runtime_event(
                    "retry",
                    model=candidate_model,
                    provider=candidate_provider,
                    attempt=attempt,
                    error="empty_response",
                )
                if attempt < max_attempts:
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue
                break

            def _bill(text: str) -> None:
                if not cost_callback:
                    return
                llm_costs = calculate_llm_cost(
                    llm_provider=candidate_provider,
                    model=candidate_model,
                    input_content=str(messages),
                    output_content=text,
                    response_metadata=provider.last_response_metadata,
                    usage_metadata=provider.last_usage_metadata,
                    request_options=provider_kwargs,
                )
                cost_callback(llm_costs)

            _bill(response)

            # Token-limit hit → continue writing and concatenate
            pieces = [response]
            continues = 0
            cont_max = _continue_max() if allow_continue else 0
            while (
                continues < cont_max
                and _output_hit_token_limit(provider.last_response_metadata)
            ):
                continues += 1
                _record_runtime_event(
                    "continue",
                    model=candidate_model,
                    provider=candidate_provider,
                    part=continues,
                    finish_reason=(provider.last_response_metadata or {}).get(
                        "finish_reason"
                    )
                    or (provider.last_response_metadata or {}).get("stop_reason"),
                )
                await _persist_runtime_trace()
                try:
                    from jobs.runtime import check_abort, get_abort_runtime

                    await check_abort(where=f"llm_continue_{continues}")
                    runtime = get_abort_runtime()
                    if runtime is not None:
                        runtime.register_llm_call(where="continue_writing")
                except ImportError:
                    pass
                cont_messages = _continue_messages(messages, "".join(pieces))
                # Prefer non-stream for continuation to avoid UI duplication noise
                cont_text = await provider.get_chat_response(
                    cont_messages, False, None, **kwargs
                )
                if not cont_text:
                    _record_runtime_event(
                        "truncate",
                        model=candidate_model,
                        reason="continue_empty",
                        parts=continues,
                    )
                    break
                _bill(cont_text)
                pieces.append(cont_text)

            if continues and not _output_hit_token_limit(provider.last_response_metadata):
                pass
            elif continues >= cont_max and _output_hit_token_limit(
                provider.last_response_metadata
            ):
                _record_runtime_event(
                    "truncate",
                    model=candidate_model,
                    reason="continue_max_reached",
                    parts=continues,
                )
                await _persist_runtime_trace()

            return "".join(pieces)

        if candidate_index < len(candidates) - 1:
            nxt = candidates[candidate_index + 1]
            logger.warning(
                "Switching Smart LLM from %s to configured fallback %s",
                candidate_model, nxt[0],
            )
            _record_runtime_event(
                "model_switch",
                from_model=candidate_model,
                from_provider=candidate_provider,
                to_model=nxt[0],
                to_provider=nxt[1],
                reason=str(last_exception)[:300] if last_exception else "failover",
            )
            await _persist_runtime_trace()

    logger.error("Failed to get a response from all configured LLM candidates")
    raise RuntimeError("Failed to get a response from all configured LLM candidates") from last_exception


async def construct_subtopics(
    task: str,
    data: str,
    config,
    subtopics: list = [],
    prompt_family: type[PromptFamily] | PromptFamily = PromptFamily,
    **kwargs
) -> list:
    """
    Construct subtopics based on the given task and data.

    Args:
        task (str): The main task or topic.
        data (str): Additional data for context.
        config: Configuration settings.
        subtopics (list, optional): Existing subtopics. Defaults to [].
        prompt_family (PromptFamily): Family of prompts
        **kwargs: Additional keyword arguments.

    Returns:
        list: A list of constructed subtopics.
    """
    try:
        parser = PydanticOutputParser(pydantic_object=Subtopics)

        prompt = PromptTemplate(
            template=prompt_family.generate_subtopics_prompt(),
            input_variables=["task", "data", "subtopics", "max_subtopics"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()},
        )

        # Structured outline planning uses STRATEGIC then FAST — not SMART. :-)
        plan_candidates = [
            (config.strategic_llm_model, config.strategic_llm_provider),
            (config.fast_llm_model, config.fast_llm_provider),
        ]
        # Deduplicate if strategic and fast point at the same model.
        seen: set[tuple[str, str | None]] = set()
        unique_candidates: list[tuple[str, str | None]] = []
        for cand in plan_candidates:
            if cand in seen:
                continue
            seen.add(cand)
            unique_candidates.append(cand)

        last_err = None
        for candidate_model, candidate_provider in unique_candidates:
            try:
                provider_kwargs = {"model": candidate_model}
                if config.llm_kwargs:
                    provider_kwargs.update(config.llm_kwargs)
                if candidate_model in SUPPORT_REASONING_EFFORT_MODELS:
                    provider_kwargs["reasoning_effort"] = ReasoningEfforts.Low.value
                else:
                    provider_kwargs["temperature"] = config.temperature
                    provider_kwargs["max_tokens"] = (
                        config.strategic_token_limit
                        if candidate_model == config.strategic_llm_model
                        else config.fast_token_limit
                    )
                provider = get_llm(candidate_provider, **provider_kwargs)
                chain = prompt | provider.llm | parser
                output = await chain.ainvoke({
                    "task": task,
                    "data": data,
                    "subtopics": subtopics,
                    "max_subtopics": config.max_subtopics
                }, **kwargs)
                return output
            except Exception as e:
                last_err = e
                logger.warning(
                    "construct_subtopics failed on %s: %s — trying next",
                    candidate_model, e,
                )
                _record_runtime_event(
                    "model_switch",
                    from_model=candidate_model,
                    reason=f"subtopics:{e}"[:300],
                )
                continue

        logger.error("Exception in parsing subtopics : \n %s", last_err)
        return subtopics

    except Exception as e:
        print("Exception in parsing subtopics : ", e)
        logger.error("Exception in parsing subtopics : \n %s", e)
        return subtopics
