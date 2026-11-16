"""LLM client factory.

Isolates the provider choice behind two helpers so the rest of the module
never imports langchain-anthropic (or any other provider package) directly.
A swap is one edit here.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from app.config import settings

logger = logging.getLogger("netracare.llm")


def _make_anthropic(model_name: str, timeout_s: float) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model_name=model_name,
        timeout=timeout_s,
        max_retries=0,  # we fail-closed on first failure; retries belong at the chain level
        api_key=settings.anthropic_api_key,
        # Explicit temperature=0 for classification + summarisation determinism.
        temperature=0,
    )


def _make_ollama(model_name: str, timeout_s: float) -> BaseChatModel:
    # Local provider for classroom use without an API key. The Anthropic
    # prompt-cache target (SC-007) does not apply here; the token-budget
    # and fail-mode commitments still do.
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model_name,
        base_url=settings.ollama_base_url,
        temperature=0,
        # Timeout threaded through client_kwargs since langchain-ollama
        # doesn't accept `timeout=` on the constructor.
        client_kwargs={"timeout": timeout_s},
    )


def _make_model(model_name: str, timeout_s: float) -> BaseChatModel:
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        return _make_anthropic(model_name, timeout_s)
    if provider == "ollama":
        return _make_ollama(model_name, timeout_s)
    raise RuntimeError(
        f"Unsupported LLM_PROVIDER={provider!r}. "
        "Supported: 'anthropic' (default), 'ollama'. See research.md D11."
    )


def _is_ollama() -> bool:
    return settings.llm_provider.lower() == "ollama"


def system_content(text: str) -> str | list[dict]:
    """Return a SystemMessage.content shaped for the active provider.

    Anthropic: a single-element list with cache_control on the stable prefix,
    so repeated calls hit the ephemeral prompt cache.
    Ollama: a plain string; Ollama has no prompt-cache concept and rejects
    the multi-part content block shape.
    """
    if _is_ollama():
        return text
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def get_fast_model() -> BaseChatModel:
    """Model for red-flag check and Fact of the Day — latency-sensitive, classification-grade."""
    name = (
        settings.ollama_model_fast if _is_ollama() else settings.llm_model_fast
    )
    return _make_model(name, settings.llm_timeout_fast)


def get_quality_model() -> BaseChatModel:
    """Model for the doctor summary — strict-instruction-following, longer output."""
    name = (
        settings.ollama_model_quality if _is_ollama() else settings.llm_model_quality
    )
    return _make_model(name, settings.llm_timeout_quality)


def log_call(chain: str, response_meta: dict[str, Any] | None, latency_ms: float) -> None:
    """Structured log line per chain call. No PHI, no prompt content."""
    usage: dict[str, Any] = {}
    if response_meta:
        # Anthropic surfaces token counts and cache stats on `usage` metadata.
        usage = response_meta.get("usage", {}) or {}
    logger.info(
        "llm_call chain=%s model=%s input_tokens=%s output_tokens=%s "
        "cache_read=%s cache_creation=%s latency_ms=%.1f",
        chain,
        (response_meta or {}).get("model", "?"),
        usage.get("input_tokens", "?"),
        usage.get("output_tokens", "?"),
        usage.get("cache_read_input_tokens", 0),
        usage.get("cache_creation_input_tokens", 0),
        latency_ms,
    )
