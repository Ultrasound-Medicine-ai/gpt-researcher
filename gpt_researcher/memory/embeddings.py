"""Embedding provider management for GPT Researcher.

This module provides the Memory class that handles embedding generation
across multiple providers (OpenAI, Cohere, Google, Ollama, etc.).

Supported providers:
    - openai: OpenAI embeddings
    - azure_openai: Azure OpenAI embeddings
    - cohere: Cohere embeddings
    - google_vertexai: Google Vertex AI embeddings
    - google_genai: Google Generative AI embeddings
    - fireworks: Fireworks AI embeddings
    - ollama: Local Ollama embeddings
    - together: Together AI embeddings
    - mistralai: Mistral AI embeddings
    - huggingface: HuggingFace embeddings
    - nomic: Nomic embeddings
    - voyageai: Voyage AI embeddings
    - dashscope: DashScope embeddings
    - matpool: Matpool OpenAI-compatible embeddings
    - bedrock: AWS Bedrock embeddings
    - aimlapi: AIML API embeddings
    - custom: Custom OpenAI-compatible API
"""

from __future__ import annotations

import os
from typing import Any, Optional

from langchain_core.embeddings import Embeddings

OPENAI_EMBEDDING_MODEL = os.environ.get(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
)

_SUPPORTED_PROVIDERS = {
    "openai",
    "azure_openai",
    "cohere",
    "gigachat",
    "google_vertexai",
    "google_genai",
    "fireworks",
    "ollama",
    "together",
    "mistralai",
    "huggingface",
    "nomic",
    "voyageai",
    "dashscope",
    "matpool",
    "custom",
    "bedrock",
    "aimlapi",
    "netmind",
    "openrouter",
    "minimax",
}


class Memory:
    """Manages embedding generation for document similarity and retrieval.

    This class provides a unified interface for generating embeddings
    using various providers. It lazily loads provider-specific dependencies
    only when needed.

    Attributes:
        _embeddings: The underlying LangChain embeddings instance.

    Example:
        ```python
        memory = Memory("openai", "text-embedding-3-small")
        embeddings = memory.get_embeddings()
        ```
    """

    def __init__(self, embedding_provider: str, model: str, **embedding_kwargs: Any):
        """Initialize the Memory with a specific embedding provider.

        Args:
            embedding_provider: The name of the embedding provider to use.
                Must be one of the supported providers (openai, cohere, etc.).
            model: The model name/ID to use for embeddings.
            **embedding_kwargs: Additional keyword arguments passed to the
                embedding provider's constructor.

        Raises:
            Exception: If the embedding provider is not supported.
        """
        _embeddings = None
        match embedding_provider:
            case "custom":
                from langchain_openai import OpenAIEmbeddings

                _embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=os.getenv("OPENAI_API_KEY", "custom"),
                    openai_api_base=os.getenv(
                        "OPENAI_BASE_URL", "http://localhost:1234/v1"
                    ),  # default for lmstudio
                    check_embedding_ctx_length=False,
                    **embedding_kwargs,
                )  # quick fix for lmstudio
            case "openai":
                from langchain_openai import OpenAIEmbeddings

                # Support custom OpenAI-compatible APIs via OPENAI_BASE_URL
                if "openai_api_base" not in embedding_kwargs and os.environ.get("OPENAI_BASE_URL"):
                    embedding_kwargs["openai_api_base"] = os.environ["OPENAI_BASE_URL"]

                _embeddings = OpenAIEmbeddings(model=model, **embedding_kwargs)
            case "azure_openai":
                from langchain_openai import AzureOpenAIEmbeddings

                _embeddings = AzureOpenAIEmbeddings(
                    model=model,
                    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                    openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
                    openai_api_version=os.environ.get(
                        "AZURE_OPENAI_API_VERSION",
                        os.environ.get("OPENAI_API_VERSION"),
                    ),
                    **embedding_kwargs,
                )
            case "cohere":
                from langchain_cohere import CohereEmbeddings

                _embeddings = CohereEmbeddings(model=model, **embedding_kwargs)
            case "google_vertexai":
                from langchain_google_vertexai import VertexAIEmbeddings

                _embeddings = VertexAIEmbeddings(model=model, **embedding_kwargs)
            case "google_genai":
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                _embeddings = GoogleGenerativeAIEmbeddings(
                    model=model, **embedding_kwargs
                )
            case "fireworks":
                from langchain_fireworks import FireworksEmbeddings

                _embeddings = FireworksEmbeddings(model=model, **embedding_kwargs)
            case "gigachat":
                from langchain_gigachat import GigaChatEmbeddings

                _embeddings = GigaChatEmbeddings(model=model, **embedding_kwargs)
            case "ollama":
                from langchain_ollama import OllamaEmbeddings

                _embeddings = OllamaEmbeddings(
                    model=model,
                    base_url=os.environ["OLLAMA_BASE_URL"],
                    **embedding_kwargs,
                )
            case "together":
                from langchain_together import TogetherEmbeddings

                _embeddings = TogetherEmbeddings(model=model, **embedding_kwargs)
            case "netmind":
                from langchain_netmind import NetmindEmbeddings

                _embeddings = NetmindEmbeddings(model=model, **embedding_kwargs)
            case "mistralai":
                from langchain_mistralai import MistralAIEmbeddings

                _embeddings = MistralAIEmbeddings(model=model, **embedding_kwargs)
            case "huggingface":
                from langchain_huggingface import HuggingFaceEmbeddings

                _embeddings = HuggingFaceEmbeddings(model_name=model, **embedding_kwargs)
            case "nomic":
                from langchain_nomic import NomicEmbeddings

                _embeddings = NomicEmbeddings(model=model, **embedding_kwargs)
            case "voyageai":
                from langchain_voyageai import VoyageAIEmbeddings

                _embeddings = VoyageAIEmbeddings(
                    voyage_api_key=os.environ["VOYAGE_API_KEY"],
                    model=model,
                    **embedding_kwargs,
                )
            case "dashscope":
                from langchain_community.embeddings import DashScopeEmbeddings

                # Quota/403 is not cured by backoff — fail over immediately. :-)
                ds_kwargs = dict(embedding_kwargs or {})
                ds_kwargs.setdefault("max_retries", 0)
                _embeddings = DashScopeEmbeddings(model=model, **ds_kwargs)
            case "matpool":
                from langchain_openai import OpenAIEmbeddings

                # OpenAI-compatible Matpool gateway (Text-Embedding-V4, etc.). :-)
                mp_kwargs = dict(embedding_kwargs or {})
                mp_kwargs.setdefault("check_embedding_ctx_length", False)
                mp_kwargs.setdefault("max_retries", 1)
                if "dimensions" not in mp_kwargs:
                    try:
                        mp_kwargs["dimensions"] = int(
                            os.getenv("EMBEDDING_DIM") or "1024"
                        )
                    except ValueError:
                        mp_kwargs["dimensions"] = 1024
                _embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=os.getenv("MATPOOL_API_KEY")
                    or os.getenv("OPENAI_API_KEY"),
                    openai_api_base=os.getenv(
                        "MATPOOL_BASE_URL", "https://token.matpool.com/v1"
                    ),
                    **mp_kwargs,
                )
            case "bedrock":
                from langchain_aws.embeddings import BedrockEmbeddings

                _embeddings = BedrockEmbeddings(model_id=model, **embedding_kwargs)
            case "aimlapi":
                from langchain_openai import OpenAIEmbeddings

                _embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=os.getenv("AIMLAPI_API_KEY"),
                    openai_api_base=os.getenv("AIMLAPI_BASE_URL", "https://api.aimlapi.com/v1"),
                    **embedding_kwargs,
                )
            case "openrouter":
                from langchain_openai import OpenAIEmbeddings

                _embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
                    openai_api_base="https://openrouter.ai/api/v1",
                    **embedding_kwargs,
                )
            case "minimax":
                from langchain_openai import OpenAIEmbeddings

                _embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=os.getenv("MINIMAX_API_KEY"),
                    openai_api_base="https://api.minimax.io/v1",
                    **embedding_kwargs,
                )
            case _:
                raise Exception("Embedding not found.")

        self._embeddings = _embeddings
        self.provider = embedding_provider
        self.model = model

    def get_embeddings(self):
        """Get the configured embeddings instance.

        Returns:
            The LangChain embeddings instance configured for this Memory.
        """
        return self._embeddings


# Known output dims — keep in sync with EMBEDDING_DIM / pgvector column. :-)
_KNOWN_EMBEDDING_DIMS: dict[tuple[str, str], int] = {
    ("dashscope", "text-embedding-v1"): 1536,
    ("dashscope", "text-embedding-v2"): 1536,
    ("dashscope", "text-embedding-v3"): 1024,
    ("dashscope", "text-embedding-v4"): 1024,
    ("matpool", "Text-Embedding-V4"): 1024,
    ("matpool", "text-embedding-v4"): 1024,
    ("openai", "text-embedding-3-small"): 1536,
    ("openai", "text-embedding-3-large"): 3072,
    ("openai", "text-embedding-ada-002"): 1536,
    ("ollama", "nomic-embed-text"): 768,
    ("ollama", "mxbai-embed-large"): 1024,
}

# Process-wide sticky success so each compress/ingest call does not re-walk the chain. :-)
_STICKY_EMBEDDING: Optional[tuple[str, str]] = None


def expected_embedding_dim() -> int:
    raw = (os.environ.get("EMBEDDING_DIM") or "1024").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 1024


def _known_dim(provider: str, model: str) -> Optional[int]:
    return _KNOWN_EMBEDDING_DIMS.get((provider.lower(), model.strip()))


def _filter_candidates_by_dim(
    candidates: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Drop known-incompatible models (e.g. ollama 768 vs pgvector 1536). :-)"""
    target = expected_embedding_dim()
    kept: list[tuple[str, str]] = []
    for p, m in candidates:
        dim = _known_dim(p, m)
        if dim is not None and dim != target:
            continue
        kept.append((p, m))
    return kept


def _embedding_candidates(provider: str, model: str) -> list[tuple[str, str]]:
    """Primary EMBEDDING plus EMBEDDING_FALLBACKS (provider:model,...)."""
    candidates: list[tuple[str, str]] = [(provider, model)]
    # Default DashScope-friendly fallbacks when unset and primary looks like dashscope
    raw = os.environ.get("EMBEDDING_FALLBACKS", "").strip()
    if not raw and provider == "dashscope" and model == "text-embedding-v2":
        raw = "dashscope:text-embedding-v1"
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        p, m = entry.split(":", 1)
        cand = (p.strip(), m.strip())
        if cand not in candidates:
            candidates.append(cand)
    return _filter_candidates_by_dim(candidates)


def create_memory_with_failover(
    embedding_provider: str,
    model: str,
    **embedding_kwargs: Any,
) -> "Memory":
    """Construct Memory with runtime embedding failover across EMBEDDING_FALLBACKS.

    Returns a Memory whose embeddings wrapper rotates models on 429/quota errors.
    If every candidate fails at use-time, callers should catch and keyword-fallback.
    """
    global _STICKY_EMBEDDING
    from gpt_researcher.utils.dep_resilience import get_circuit, record_degradation

    embed_cb = get_circuit("embed")
    candidates = _embedding_candidates(embedding_provider, model)

    if not embed_cb.allow():
        record_degradation("embedding", "circuit_open", rag_degraded=True)
        mem = _UnavailableMemory()
        return mem  # type: ignore[return-value]

    if not candidates:
        record_degradation(
            "rag",
            "no_dim_compatible_embedding",
            rag_degraded=True,
        )
        return _UnavailableMemory()  # type: ignore[return-value]

    start_index = 0
    if _STICKY_EMBEDDING and _STICKY_EMBEDDING in candidates:
        start_index = candidates.index(_STICKY_EMBEDDING)

    last_err: Optional[Exception] = None
    order = list(range(start_index, len(candidates))) + list(range(0, start_index))
    for i in order:
        p, m = candidates[i]
        try:
            base = Memory(p, m, **embedding_kwargs)
            wrapper = _FailoverEmbeddings(
                candidates=candidates,
                embedding_kwargs=embedding_kwargs,
                start_index=i,
            )
            base._embeddings = wrapper
            base.provider = p
            base.model = m
            return base
        except Exception as exc:
            last_err = exc
            record_degradation(
                "embedding",
                f"init_failed:{exc}"[:200],
                from_model=f"{p}:{m}",
            )
            continue

    record_degradation(
        "rag",
        f"all_embedding_unavailable:{last_err}"[:280] if last_err else "all_embedding_unavailable",
        rag_degraded=True,
    )
    return _UnavailableMemory()  # type: ignore[return-value]


class _FailoverEmbeddings(Embeddings):
    """Try embedding models in order; rotate on runtime failures."""

    def __init__(
        self,
        candidates: list[tuple[str, str]],
        embedding_kwargs: dict[str, Any],
        start_index: int = 0,
    ):
        self.candidates = candidates
        self.embedding_kwargs = embedding_kwargs
        self.index = max(0, start_index)
        self._inner = None
        self._ensure_inner()

    def _ensure_inner(self):
        if self._inner is not None:
            return
        p, m = self.candidates[self.index]
        self._inner = Memory(p, m, **self.embedding_kwargs).get_embeddings()

    def _is_failover_error(self, exc: BaseException) -> bool:
        msg = str(exc).lower()
        return any(
            x in msg
            for x in (
                "429",
                "403",
                "permission",
                "freetier",
                "free tier",
                "allocationquota",
                "rate limit",
                "rate_limit",
                "quota",
                "insufficient",
                "timeout",
                "overloaded",
                "embedding_unavailable",
                "503",
                "capacity",
            )
        )

    def _call_with_failover(self, method: str, *args, **kwargs):
        global _STICKY_EMBEDDING
        from gpt_researcher.utils.dep_resilience import get_circuit, record_degradation

        embed_cb = get_circuit("embed")
        last_err: Optional[Exception] = None
        for i in range(self.index, len(self.candidates)):
            if not embed_cb.allow():
                break
            try:
                if i != self.index or self._inner is None:
                    p, m = self.candidates[i]
                    self._inner = Memory(p, m, **self.embedding_kwargs).get_embeddings()
                    if i != self.index:
                        prev = self.candidates[self.index]
                        record_degradation(
                            "embedding",
                            "runtime_switch",
                            from_model=f"{prev[0]}:{prev[1]}",
                            to_model=f"{p}:{m}",
                        )
                    self.index = i
                fn = getattr(self._inner, method)
                result = fn(*args, **kwargs)
                embed_cb.record_success()
                _STICKY_EMBEDDING = self.candidates[self.index]
                return result
            except Exception as exc:
                last_err = exc
                embed_cb.record_failure(str(exc))
                if self._is_failover_error(exc):
                    continue
                raise
        record_degradation(
            "rag",
            f"embedding_exhausted:{last_err}"[:280] if last_err else "embedding_exhausted",
            rag_degraded=True,
        )
        raise RuntimeError("embedding_unavailable") from last_err

    def embed_documents(self, texts):
        return self._call_with_failover("embed_documents", texts)

    def embed_query(self, text):
        return self._call_with_failover("embed_query", text)

    async def aembed_documents(self, texts):
        return self._call_with_failover("aembed_documents", texts)

    async def aembed_query(self, text):
        return self._call_with_failover("aembed_query", text)


class _UnavailableMemory:
    """Stand-in Memory when every embedding model is unavailable."""

    provider = "none"
    model = "unavailable"

    def __init__(self):
        self._embeddings = _FailingEmbeddings()

    def get_embeddings(self):
        return self._embeddings


class _FailingEmbeddings:
    def embed_documents(self, texts):
        raise RuntimeError("embedding_unavailable")

    def embed_query(self, text):
        raise RuntimeError("embedding_unavailable")

    async def aembed_documents(self, texts):
        raise RuntimeError("embedding_unavailable")

    async def aembed_query(self, text):
        raise RuntimeError("embedding_unavailable")
