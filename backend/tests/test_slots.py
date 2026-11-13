from __future__ import annotations

from datetime import date, datetime

from app.slots import free_slots
from tests.conftest import FIXED_NOW, make_appointment


def test_empty_on_sunday(session, seed):
    assert free_slots("D1", date(2026, 11, 8), "new", session=session, now=FIXED_NOW) == []


def test_empty_on_holiday(session, seed):
    # 2026-11-09 is seeded as Diwali.
    assert free_slots("D1", date(2026, 11, 9), "new", session=session, now=FIXED_NOW) == []


def test_rao_thursday_am_empty_pm_full(session, seed):
    thu = date(2026, 11, 5)  # Thursday — D1 AM SURGERY, PM OPD
    slots = free_slots("D1", thu, "new", session=session, now=FIXED_NOW)
    assert all(s.hour >= 14 for s in slots)
    assert datetime.combine(thu, datetime.min.time()).replace(hour=14, minute=0) in slots


def test_iyer_thursday_fully_empty(session, seed):
    assert free_slots("D2", date(2026, 11, 5), "new", session=session, now=FIXED_NOW) == []


def test_new_visit_slot_count_wed_full_day(session, seed):
    wed = date(2026, 11, 4)
    slots = free_slots("D1", wed, "new", session=session, now=FIXED_NOW)
    # AM: 09:00..12:40 inclusive on 10-min marks → 23 starts.
    # PM: 14:00..17:40 inclusive on 10-min marks → 23 starts.
    assert len(slots) == 46


def test_overlap_removes_slot(session, seed):
    wed_10 = datetime(2026, 11, 4, 10, 0, 0)
    make_appointment(session, start=wed_10, patient_id="P02", doctor_id="D1")
    slots = free_slots("D1", wed_10.date(), "new", session=session, now=FIXED_NOW)
    # The 10:00 slot and overlapping ones (09:50, 10:10) are gone.
    for gone in (wed_10, wed_10.replace(hour=9, minute=50), wed_10.replace(minute=10)):
        assert gone not in slots
