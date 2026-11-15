"""Doctor summary chain. Fails OPEN: the endpoint catches
`SummaryUnavailable` and returns a fixed fallback alongside the raw notes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.llm.client import get_quality_model, log_call

_PROMPT_PATH = Path(__file__).parent / "prompts" / "summary.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


class SummaryUnavailable(Exception):
    """Any failure during doctor-summary generation. Endpoint renders fallback."""


def _system_block() -> dict:
    return {
        "type": "text",
        "text": _SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }


def _format_user_block(
    *,
    age: int | None,
    general_health: str | None,
    allergies: str | None,
    today_reason: str | None,
    past_visits: list[dict[str, Any]],
) -> str:
    profile_parts = []
    if age is not None:
        profile_parts.append(f"Age: {age}")
    if general_health:
        profile_parts.append(f"General health: {general_health}")
    if allergies:
        profile_parts.append(f"Allergies: {allergies}")
    profile = "\n".join(profile_parts) if profile_parts else "Profile: not recorded"

    today = f"Today's reason: {today_reason}" if today_reason else "Today's reason: not recorded"

    if past_visits:
        visits_json = json.dumps(past_visits, indent=2)
        visits_block = f"Past completed visits (newest first):\n{visits_json}"
    else:
        visits_block = "Past completed visits: none"

    return f"{profile}\n\n{today}\n\n{visits_block}"


def summarize_patient(
    *,
    age: int | None,
    general_health: str | None,
    allergies: str | None,
    today_reason: str | None,
    past_visits: list[dict[str, Any]],
) -> str:
    model = get_quality_model()
    parser = StrOutputParser()

    user_text = _format_user_block(
        age=age,
        general_health=general_health,
        allergies=allergies,
        today_reason=today_reason,
        past_visits=past_visits,
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
        raise SummaryUnavailable(f"llm call failed: {exc!r}") from exc
    latency_ms = (time.monotonic() - start) * 1000

    meta = getattr(response, "response_metadata", None)
    log_call("summary", meta, latency_ms)

    usage = (meta or {}).get("usage") or {}
    input_tokens = usage.get("input_tokens")
    if input_tokens is not None and input_tokens > settings.llm_max_tokens_summary:
        raise SummaryUnavailable(
            f"input tokens {input_tokens} > budget {settings.llm_max_tokens_summary}"
        )

    cleaned = text.strip().strip('"').strip()
    if not cleaned:
        raise SummaryUnavailable("empty summary")
    return cleaned
