"""Security-adjacent LLM tests.

Enforce conventions §10 invariants that an automated check can verify:
- The cacheable stable prefix of every LLM prompt MUST contain zero PHI.
- The emergency message, Fact caveat, and summary fallback MUST live in
  code constants, NEVER inside the LLM-facing prompt files (a prompt
  regression must not be able to weaken them).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.constants import EMERGENCY_MESSAGE, FACT_CAVEAT, SUMMARY_FALLBACK

_PROMPT_DIR = Path(__file__).parent.parent / "app" / "llm" / "prompts"

# Strings that would only appear in a prompt prefix if a developer leaked
# real patient-specific data into it. These are shaped around the data
# pack 2 patient names + mobile prefix — if any of these show up in a
# prompt file the test fails, and the security agent reviews.
_PHI_MARKERS = (
    "P01", "P02", "P03", "P04", "P05",
    "Asha", "Rohan", "Lakshmi", "Fatima", "Sunita",
    "9000000",  # mobile prefix used in the data pack
)


@pytest.mark.parametrize("prompt_file", sorted(_PROMPT_DIR.glob("*.md")))
def test_prompt_prefix_contains_no_PHI(prompt_file: Path):
    text = prompt_file.read_text(encoding="utf-8")
    for marker in _PHI_MARKERS:
        assert marker not in text, (
            f"{prompt_file.name}: leaked PHI marker {marker!r}. "
            "Patient data belongs in the volatile suffix only (conventions §10)."
        )


def test_emergency_message_not_in_any_prompt_file():
    # EMERGENCY_MESSAGE is the clinic's safety contract. It MUST be set
    # by the backend; a prompt must never produce it (otherwise a prompt
    # regression could weaken the wording).
    for p in _PROMPT_DIR.glob("*.md"):
        assert EMERGENCY_MESSAGE not in p.read_text(encoding="utf-8"), p.name


def test_fact_caveat_not_in_any_prompt_file():
    for p in _PROMPT_DIR.glob("*.md"):
        assert FACT_CAVEAT not in p.read_text(encoding="utf-8"), p.name


def test_summary_fallback_not_in_any_prompt_file():
    for p in _PROMPT_DIR.glob("*.md"):
        assert SUMMARY_FALLBACK not in p.read_text(encoding="utf-8"), p.name


def test_fact_prompt_explicitly_forbids_naming_conditions():
    # Weaker: not a semantic check, but ensures the Fact prompt's
    # prohibition on conditions / treatments / medicines / brands is
    # still in the text. If someone edits the prompt and drops this,
    # the test catches it.
    text = (_PROMPT_DIR / "fact.md").read_text(encoding="utf-8").lower()
    for required in ("condition", "treatment", "medicine", "brand"):
        assert required in text, f"fact.md no longer mentions {required!r}"


def test_summary_prompt_forbids_adding_diagnosis_or_advice():
    text = (_PROMPT_DIR / "summary.md").read_text(encoding="utf-8").lower()
    for required in ("restate", "diagnosis", "advice"):
        assert required in text, f"summary.md no longer mentions {required!r}"


def test_red_flag_prompt_covers_all_five_categories():
    text = (_PROMPT_DIR / "red_flag.md").read_text(encoding="utf-8")
    for cat in (
        "sudden_vision_loss",
        "curtain_or_shadow",
        "floaters_or_flashes",
        "chemical_or_injury",
        "severe_pain_headache_haloes",
    ):
        assert cat in text, f"red_flag.md missing category {cat!r}"
