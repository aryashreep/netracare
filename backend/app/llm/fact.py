"""Fact of the Day chain. Fails OPEN: the endpoint catches
`FactUnavailable` and serves a fixed fallback with the standard caveat."""

from __future__ import annotations

import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.llm.client import get_fast_model, log_call

_PROMPT_PATH = Path(__file__).parent / "prompts" / "fact.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


class FactUnavailable(Exception):
    """Any failure during Fact of the Day. The endpoint renders the fallback."""


def _system_block() -> dict:
    return {
        "type": "text",
        "text": _SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }


def generate_fact(previous: str | None = None) -> str:
    model = get_fast_model()
    parser = StrOutputParser()

    user_text = (
        "Return a fresh fact. The patient has already seen this previous fact, "
        "so pick a different topic:\n\n" + previous
        if previous
        else "Return a fresh fact for a patient who just signed in."
    )

    messages = [
        SystemMessage(content=[_system_block()]),
        HumanMessage(content=user_text),
    ]

    start = time.monotonic()
    try:
        response = model.invoke(messages)
        text = parser.invoke(response)
    except Exception as exc:
        raise FactUnavailable(f"llm call failed: {exc!r}") from exc
    latency_ms = (time.monotonic() - start) * 1000

    meta = getattr(response, "response_metadata", None)
    log_call("fact", meta, latency_ms)

    usage = (meta or {}).get("usage") or {}
    input_tokens = usage.get("input_tokens")
    if input_tokens is not None and input_tokens > settings.llm_max_tokens_fact:
        raise FactUnavailable(
            f"input tokens {input_tokens} > budget {settings.llm_max_tokens_fact}"
        )

    cleaned = text.strip().strip('"').strip()
    if not cleaned:
        raise FactUnavailable("empty fact")
    return cleaned
