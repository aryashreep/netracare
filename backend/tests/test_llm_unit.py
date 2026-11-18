"""Unit tests for the LLM module's non-LLM parts.

These exercise the pure Python we control: constants, prompt assembly,
Pydantic parsers, and the token-budget / schema-consistency guards. No
provider is called; the LLM itself is replaced with a stub when
needed. These tests run on every CI invocation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.constants import (
    EMERGENCY_MESSAGE,
    FACT_CAVEAT,
    FACT_FALLBACK,
    SUMMARY_FALLBACK,
)
from app.llm.red_flag import (
    RED_FLAG_CATEGORIES,
    RedFlagCheckError,
    RedFlagResult,
    check_red_flags,
)
from app.llm.summary import _format_user_block

# ---- Safety constants ----


def test_emergency_message_is_verbatim_handout_text():
    # Handout §04-R4 — safety contract. Renaming this breaks the clinic's
    # red-flag UX. Keep this assertion verbatim.
    assert EMERGENCY_MESSAGE == (
        "What you describe needs urgent attention. "
        "Please come to the clinic now or go to the nearest emergency department. "
        "Our staff have been notified."
    )


def test_fact_caveat_is_verbatim_handout_text():
    assert FACT_CAVEAT == "General information, not medical advice"


def test_fact_fallback_is_a_non_empty_general_fact():
    # Fallback is shown with the caveat — must itself follow the rule
    # "no condition, treatment, medicine, or product name" so Fact never
    # ships advice even in degraded mode.
    text = FACT_FALLBACK.lower()
    assert len(FACT_FALLBACK) > 20
    for forbidden in ("glaucoma", "cataract", "drops", "medication", "doctor"):
        assert forbidden not in text


def test_summary_fallback_points_the_doctor_at_the_raw_notes():
    assert "notes below" in SUMMARY_FALLBACK.lower()


def test_five_red_flag_categories_match_handout():
    # Any change here needs a spec amendment — Iter 3 chat routes on these.
    assert RED_FLAG_CATEGORIES == (
        "sudden_vision_loss",
        "curtain_or_shadow",
        "floaters_or_flashes",
        "chemical_or_injury",
        "severe_pain_headache_haloes",
    )


# ---- RedFlagResult parsing ----


def test_red_flag_result_accepts_a_valid_flag():
    r = RedFlagResult(
        red_flag=True,
        category="sudden_vision_loss",
        why="Patient reports sudden vision loss.",
    )
    assert r.red_flag is True
    assert r.category == "sudden_vision_loss"


def test_red_flag_result_accepts_the_benign_shape():
    r = RedFlagResult(red_flag=False, category=None, why="Routine")
    assert r.red_flag is False
    assert r.category is None


def test_red_flag_result_rejects_an_unknown_category():
    with pytest.raises(ValidationError):
        RedFlagResult(red_flag=True, category="made_up", why="oops")  # type: ignore[arg-type]


def test_red_flag_result_caps_the_why_length():
    with pytest.raises(ValidationError):
        RedFlagResult(red_flag=False, category=None, why="x" * 301)


# ---- check_red_flags shape guards (no LLM call) ----


def test_check_red_flags_refuses_an_empty_reason():
    with pytest.raises(RedFlagCheckError):
        check_red_flags("   ")


def test_check_red_flags_refuses_an_over_budget_reason():
    with pytest.raises(RedFlagCheckError):
        check_red_flags("A" * 301)


# ---- check_red_flags LLM-path consistency guards ----


class _StubModel:
    """Stand-in for a LangChain chat model with .with_structured_output()."""

    def __init__(self, parsed, raw_meta=None):
        self._parsed = parsed
        self._raw_meta = raw_meta or {"model": "stub", "usage": {"input_tokens": 100}}

    def with_structured_output(self, *_a, **_kw):
        return self

    def invoke(self, _messages):
        class _Raw:
            response_metadata = self._raw_meta

        return {
            "parsed": self._parsed,
            "raw": _Raw(),
        }


def test_check_red_flags_refuses_when_category_missing_for_a_flag(monkeypatch):
    # Models sometimes skip the category. Fail CLOSED rather than guess.
    from app.llm import red_flag as mod

    stub = _StubModel(
        parsed=RedFlagResult(red_flag=True, category=None, why="unknown"),
    )
    monkeypatch.setattr(mod, "get_fast_model", lambda: stub)
    with pytest.raises(RedFlagCheckError):
        check_red_flags("I suddenly cannot see")


def test_check_red_flags_clears_a_stray_category_on_benign_output(monkeypatch):
    # Safe direction: a category without a flag is just dropped.
    from app.llm import red_flag as mod

    stub = _StubModel(
        parsed=RedFlagResult(
            red_flag=False, category="sudden_vision_loss", why="stray"
        ),
    )
    monkeypatch.setattr(mod, "get_fast_model", lambda: stub)
    r = check_red_flags("Routine check")
    assert r.red_flag is False
    assert r.category is None


def test_check_red_flags_refuses_when_input_tokens_exceed_budget(monkeypatch):
    from app.llm import red_flag as mod

    stub = _StubModel(
        parsed=RedFlagResult(red_flag=False, category=None, why="ok"),
        raw_meta={"model": "stub", "usage": {"input_tokens": 99999}},
    )
    monkeypatch.setattr(mod, "get_fast_model", lambda: stub)
    with pytest.raises(RedFlagCheckError):
        check_red_flags("Routine check")


def test_check_red_flags_refuses_when_underlying_model_raises(monkeypatch):
    class _BoomModel:
        def with_structured_output(self, *_a, **_kw):
            return self

        def invoke(self, _m):
            raise TimeoutError("fake")

    from app.llm import red_flag as mod

    monkeypatch.setattr(mod, "get_fast_model", lambda: _BoomModel())
    with pytest.raises(RedFlagCheckError):
        check_red_flags("Routine check")


# ---- Summary prompt assembly ----


def test_summary_user_block_omits_missing_profile_fields():
    txt = _format_user_block(
        age=None,
        general_health=None,
        allergies=None,
        today_reason=None,
        past_visits=[],
    )
    # No fabricated placeholders ("No X recorded") — just absence.
    assert "Age:" not in txt
    assert "General health:" not in txt
    assert "Allergies:" not in txt
    assert "Profile: not recorded" in txt
    assert "Past completed visits: none" in txt


def test_summary_user_block_includes_recorded_profile_fields():
    txt = _format_user_block(
        age=66,
        general_health="Type 2 diabetes",
        allergies="Sulfa",
        today_reason="Follow-up",
        past_visits=[
            {
                "date": "2026-01-01",
                "doctor_name": "Dr. Iyer",
                "speciality": "Glaucoma",
                "doctor_note": "note",
            }
        ],
    )
    assert "Age: 66" in txt
    assert "General health: Type 2 diabetes" in txt
    assert "Allergies: Sulfa" in txt
    assert "Today's reason: Follow-up" in txt
    assert "Dr. Iyer" in txt  # doctor name reaches the LLM — required by FR-021
    assert "Past completed visits" in txt
