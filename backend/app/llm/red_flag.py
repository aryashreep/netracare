"""Red-flag classifier.

The only LLM chain in the system that is safety-critical. Fails CLOSED:
every exception path (timeout, HTTP error, parse error, token-budget
overrun) maps to `RedFlagCheckError`, which the booking router converts
to HTTP 503 `RED_FLAG_CHECK_UNAVAILABLE`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.llm.client import get_fast_model, log_call

RED_FLAG_CATEGORIES = (
    "sudden_vision_loss",
    "curtain_or_shadow",
    "floaters_or_flashes",
    "chemical_or_injury",
    "severe_pain_headache_haloes",
)

Category = Literal[
    "sudden_vision_loss",
    "curtain_or_shadow",
    "floaters_or_flashes",
    "chemical_or_injury",
    "severe_pain_headache_haloes",
]


class RedFlagResult(BaseModel):
    red_flag: bool
    category: Category | None = None
    why: str = Field(max_length=300)


class RedFlagCheckError(Exception):
    """Any failure during the red-flag check. Booking MUST be refused on this."""


_PROMPT_PATH = Path(__file__).parent / "prompts" / "red_flag.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

# Rough-cut character ceiling. Prompt + 300-char reason stays comfortably under 2k tokens.
# Real token counting is done on the response metadata; this is a pre-send guard.
_MAX_REASON_CHARS = 300


def _system_block() -> dict:
    """Cacheable stable prefix. Anthropic cache-control marks it for the ephemeral cache."""
    return {
        "type": "text",
        "text": _SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }


def check_red_flags(reason: str) -> RedFlagResult:
    """Classify an appointment reason.

    Fails closed on timeout, API error, parse error, or budget overrun by
    raising RedFlagCheckError. Callers (the booking router) MUST refuse the
    booking on this exception.
    """
    if not reason or not reason.strip():
        # Empty reasons shouldn't reach this function (the schema rejects them),
        # but fail safe here too.
        raise RedFlagCheckError("empty reason")

    if len(reason) > _MAX_REASON_CHARS:
        # Budget guard: reason is already capped at 300 chars by the schema;
        # if someone bypasses that, fail closed rather than silently truncating.
        raise RedFlagCheckError(
            f"reason too long for budget: {len(reason)} > {_MAX_REASON_CHARS} chars"
        )

    model = get_fast_model().with_structured_output(RedFlagResult, include_raw=True)

    # Anthropic multi-part content: cacheable system block + volatile user suffix.
    messages = [
        SystemMessage(content=[_system_block()]),
        HumanMessage(content=f"Patient reason:\n{reason.strip()}"),
    ]

    start = time.monotonic()
    try:
        response = model.invoke(messages)
    except Exception as exc:
        raise RedFlagCheckError(f"llm call failed: {exc!r}") from exc
    latency_ms = (time.monotonic() - start) * 1000

    parsed = response.get("parsed") if isinstance(response, dict) else None
    raw = response.get("raw") if isinstance(response, dict) else None
    meta = getattr(raw, "response_metadata", None) if raw is not None else None
    log_call("red_flag", meta, latency_ms)

    if parsed is None:
        raise RedFlagCheckError("parser returned no RedFlagResult")

    try:
        # with_structured_output already returns a RedFlagResult; re-validate
        # defensively (model_validate is a no-op when it already is one).
        if isinstance(parsed, RedFlagResult):
            result = parsed
        else:
            result = RedFlagResult.model_validate(parsed)
    except ValidationError as exc:
        raise RedFlagCheckError(f"invalid red-flag schema: {exc}") from exc

    # Enforce category consistency with the red_flag bit.
    if result.red_flag and result.category is None:
        raise RedFlagCheckError("red_flag=true but category is null")
    if not result.red_flag and result.category is not None:
        # Model got carried away. Treat as not-flagged with no category.
        result = result.model_copy(update={"category": None})

    # Input-token budget check: if the measured input blew past the ceiling,
    # fail closed. This protects us from a future prompt change that
    # silently grows the prefix.
    usage = (meta or {}).get("usage") or {}
    input_tokens = usage.get("input_tokens")
    if input_tokens is not None and input_tokens > settings.llm_max_tokens_red_flag:
        raise RedFlagCheckError(
            f"input tokens {input_tokens} > budget {settings.llm_max_tokens_red_flag}"
        )

    return result
