"""
Stretch-goal harness. Loads data-pack-01/stretch/rule_tests.csv (38 cases) and runs each
against the rules engine using the fixed clock CLINIC_NOW=2026-11-02T10:00:00.

Marked `skip` by default — depends on also loading stretch/appointments_seed.csv into the
test DB, which is deliberately left for the stretch-goal task. Unskip when you wire the
seed-import helper.
"""

import csv
from pathlib import Path

import pytest

STRETCH_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "data-pack-01" / "stretch"


@pytest.mark.skip(reason="stretch goal — requires seeding stretch/appointments_seed.csv")
def test_38_rule_cases(session, seed):
    with (STRETCH_DIR / "rule_tests.csv").open() as f:
        cases = list(csv.DictReader(f))
    assert len(cases) == 38
    # Walk each case: book / cancel / reschedule; assert expected == allowed/refused and
    # (for refused) that reason_code matches. Implementation deferred.
    for _c in cases:
        pass
