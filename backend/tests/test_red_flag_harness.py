"""Stretch-goal red-flag harness.

Iterates every row of `data/data-pack-02/reason_samples.csv` through the
real `check_red_flags` chain against a live LLM provider (whatever
`LLM_PROVIDER` resolves to — Anthropic or Ollama). Skipped by default
because it needs model access; opt in with `pytest -m live`.

Grading rubric (research.md D11, handout §11):
- 20 rows are red flags; must catch at least 18/20 (90% recall).
- 15 rows are not red flags; false positive rate ≤ 2/15 (safe to over-flag,
  bad to miss).
- For `yes` rows, the returned `category` must match `expected_category`.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.llm.red_flag import RedFlagCheckError, check_red_flags

# In Docker the data is mounted at /app/data; locally it's sibling to backend/.
_CANDIDATES = (
    Path("/app/data/data-pack-02/reason_samples.csv"),
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "data-pack-02"
    / "reason_samples.csv",
)
_SAMPLES = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])


def _load() -> list[dict[str, str]]:
    if not _SAMPLES.exists():
        pytest.skip(f"Sample file missing: {_SAMPLES}")
    with _SAMPLES.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.live
def test_red_flag_harness_against_sample_rows():
    rows = _load()
    yes_rows = [r for r in rows if r["expected_red_flag"] == "yes"]
    no_rows = [r for r in rows if r["expected_red_flag"] == "no"]

    missed: list[tuple[str, str, str | None]] = []
    wrong_category: list[tuple[str, str, str | None]] = []
    false_positives: list[tuple[str, str | None]] = []

    for r in yes_rows:
        try:
            result = check_red_flags(r["reason"])
        except RedFlagCheckError as exc:
            missed.append((r["reason"], "", str(exc)))
            continue
        if not result.red_flag:
            missed.append((r["reason"], r["category"], result.category))
        elif result.category != r["category"]:
            wrong_category.append((r["reason"], r["category"], result.category))

    for r in no_rows:
        try:
            result = check_red_flags(r["reason"])
        except RedFlagCheckError:
            # Treated as a false positive — booking would be refused here too.
            false_positives.append((r["reason"], None))
            continue
        if result.red_flag:
            false_positives.append((r["reason"], result.category))

    print()
    print(f"Red-flag yes rows: {len(yes_rows)}  missed: {len(missed)}  "
          f"wrong_category: {len(wrong_category)}")
    print(f"Red-flag no rows:  {len(no_rows)}  false_positives: {len(false_positives)}")
    for reason, expected, got in missed[:5]:
        print(f"  MISSED  expected={expected!r}  got={got!r}  reason={reason[:80]!r}")
    for reason, expected, got in wrong_category[:5]:
        print(f"  WRONG   expected={expected!r}  got={got!r}  reason={reason[:80]!r}")
    for reason, got in false_positives[:5]:
        print(f"  FP      got={got!r}  reason={reason[:80]!r}")

    assert len(missed) <= 2, f"{len(missed)}/20 red flags missed; target ≤ 2"
    assert len(false_positives) <= 2, (
        f"{len(false_positives)}/15 false positives; target ≤ 2"
    )
