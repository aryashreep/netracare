"""LLM module. One chain per feature, each `prompt | model | parser`.

Public API:
- check_red_flags(reason) -> RedFlagResult | raises RedFlagCheckError
- generate_fact(previous) -> str | raises FactUnavailable
- summarize_patient(profile, today_reason, past_visits) -> str | raises SummaryUnavailable
"""

from app.llm.fact import FactUnavailable, generate_fact
from app.llm.red_flag import (
    RED_FLAG_CATEGORIES,
    RedFlagCheckError,
    RedFlagResult,
    check_red_flags,
)
from app.llm.summary import SummaryUnavailable, summarize_patient

__all__ = [
    "check_red_flags",
    "RedFlagResult",
    "RedFlagCheckError",
    "RED_FLAG_CATEGORIES",
    "generate_fact",
    "FactUnavailable",
    "summarize_patient",
    "SummaryUnavailable",
]
