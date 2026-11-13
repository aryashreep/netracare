"""
One focused test per canonical reason code. All 17 must appear in REASON_CODES, and the
rule engine must raise each code when its specific condition is met.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session

from app.errors import REASON_CODES, RuleError
from app.models import Patient, WeeklyScheduleEntry
from app.rules import validate_booking, validate_cancel, validate_complete
from tests.conftest import FIXED_NOW, make_appointment

# A good Wednesday (2026-11-04) is a valid OPD AM day for Dr. Rao.
NEXT_WEDNESDAY = datetime(2026, 11, 4, 10, 0, 0)


def _book(session: Session, **overrides):
    defaults = dict(
        doctor_id="D1",
        patient_id="P01",
        speciality="Cataract",
        visit_type="new",
        start_ts=NEXT_WEDNESDAY,
        session=session,
        now=FIXED_NOW,
    )
    defaults.update(overrides)
    return validate_booking(**defaults)


# ---- Sanity: contract shape ----


def test_17_canonical_codes_frozen():
    assert len(REASON_CODES) == 17


# ---- Happy path ----


def test_happy_path_booking(session, seed):
    end = _book(session)
    assert end == NEXT_WEDNESDAY + timedelta(minutes=20)


# ---- Each code ----


def test_INVALID_START_TIME(session, seed):
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=NEXT_WEDNESDAY.replace(minute=7))
    assert e.value.code == "INVALID_START_TIME"


def test_IN_PAST(session, seed):
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=FIXED_NOW - timedelta(hours=1))
    assert e.value.code == "IN_PAST"


def test_BEYOND_30_DAYS(session, seed):
    far = FIXED_NOW + timedelta(days=31)
    # Align to 10-minute mark and a sensible OPD slot.
    far = far.replace(hour=10, minute=0, second=0, microsecond=0)
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=far)
    assert e.value.code == "BEYOND_30_DAYS"


def test_CLINIC_CLOSED_sunday(session, seed):
    sunday = datetime(2026, 11, 8, 10, 0, 0)  # Sunday
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=sunday)
    assert e.value.code == "CLINIC_CLOSED"


def test_HOLIDAY(session, seed):
    holiday_mon = datetime(2026, 11, 9, 10, 0, 0)  # Diwali, seeded
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=holiday_mon)
    assert e.value.code == "HOLIDAY"


def test_OUTSIDE_SESSION_lunch(session, seed):
    lunch = NEXT_WEDNESDAY.replace(hour=13, minute=30)
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=lunch)
    assert e.value.code == "OUTSIDE_SESSION"


def test_ENDS_AFTER_SESSION(session, seed):
    # New consult at 12:50 would end at 13:10, past AM close.
    late = NEXT_WEDNESDAY.replace(hour=12, minute=50)
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=late)
    assert e.value.code == "ENDS_AFTER_SESSION"


def test_DOCTOR_OFF(session, seed):
    # Dr. Iyer is OFF on Thursdays — pick 2026-11-05 Thu.
    thu = datetime(2026, 11, 5, 10, 0, 0)
    with pytest.raises(RuleError) as e:
        _book(session, doctor_id="D2", speciality="Glaucoma", start_ts=thu)
    assert e.value.code == "DOCTOR_OFF"


def test_SURGERY_SESSION(session, seed):
    # Dr. Rao's Thu AM is SURGERY — pick 2026-11-05 Thu 10:00.
    thu_am = datetime(2026, 11, 5, 10, 0, 0)
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=thu_am)
    assert e.value.code == "SURGERY_SESSION"


def test_SPECIALITY_MISMATCH(session, seed):
    # Dr. Khan does not cover Glaucoma.
    with pytest.raises(RuleError) as e:
        _book(session, doctor_id="D4", speciality="Glaucoma")
    assert e.value.code == "SPECIALITY_MISMATCH"


def test_DOUBLE_BOOKED(session, seed):
    make_appointment(session, start=NEXT_WEDNESDAY, patient_id="P02")
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=NEXT_WEDNESDAY)
    assert e.value.code == "DOUBLE_BOOKED"


def test_ACTIVE_BOOKING_EXISTS(session, seed):
    # P01 already has a Cataract booking.
    make_appointment(session, start=NEXT_WEDNESDAY, patient_id="P01")
    with pytest.raises(RuleError) as e:
        _book(session, start_ts=NEXT_WEDNESDAY.replace(hour=11))
    assert e.value.code == "ACTIVE_BOOKING_EXISTS"


def test_NO_PREVIOUS_VISIT(session, seed):
    with pytest.raises(RuleError) as e:
        _book(session, visit_type="follow_up")
    assert e.value.code == "NO_PREVIOUS_VISIT"


def test_FOLLOW_UP_DIFFERENT_DOCTOR(session, seed):
    # P01 has a completed Cataract visit with D1; try follow-up with D2 (also Cataract).
    past = FIXED_NOW - timedelta(days=5)
    past = past.replace(hour=10, minute=0, second=0, microsecond=0)
    make_appointment(session, start=past, status="completed", doctor_id="D1")
    with pytest.raises(RuleError) as e:
        _book(session, doctor_id="D2", visit_type="follow_up")
    assert e.value.code == "FOLLOW_UP_DIFFERENT_DOCTOR"


def test_follow_up_with_same_doctor_succeeds(session, seed):
    past = FIXED_NOW - timedelta(days=5)
    past = past.replace(hour=10, minute=0, second=0, microsecond=0)
    make_appointment(session, start=past, status="completed", doctor_id="D1")
    end = _book(session, visit_type="follow_up")
    assert end == NEXT_WEDNESDAY + timedelta(minutes=10)


# ---- Cancel-side codes ----


def test_cancel_INSIDE_2_HOURS(session, seed):
    soon = FIXED_NOW + timedelta(hours=1, minutes=30)
    soon = soon.replace(minute=0, second=0, microsecond=0)
    appt = make_appointment(session, start=soon, patient_id="P01")
    with pytest.raises(RuleError) as e:
        validate_cancel(appt, "patient", "P01", now=FIXED_NOW)
    assert e.value.code == "INSIDE_2_HOURS"


def test_cancel_outside_2_hours_allowed(session, seed):
    later = FIXED_NOW + timedelta(hours=5)
    later = later.replace(minute=0, second=0, microsecond=0)
    appt = make_appointment(session, start=later, patient_id="P01")
    validate_cancel(appt, "patient", "P01", now=FIXED_NOW)  # no raise


def test_cancel_staff_can_override_2_hours(session, seed):
    soon = FIXED_NOW + timedelta(hours=1)
    soon = soon.replace(minute=0, second=0, microsecond=0)
    appt = make_appointment(session, start=soon, patient_id="P01")
    validate_cancel(appt, "staff", "", now=FIXED_NOW)  # no raise


def test_cancel_NOT_YOUR_APPOINTMENT(session, seed):
    appt = make_appointment(session, start=NEXT_WEDNESDAY, patient_id="P02")
    with pytest.raises(PermissionError):
        validate_cancel(appt, "patient", "P01", now=FIXED_NOW)


def test_cancel_NOT_ACTIVE(session, seed):
    appt = make_appointment(session, start=NEXT_WEDNESDAY, patient_id="P01", status="completed")
    with pytest.raises(RuleError) as e:
        validate_cancel(appt, "staff", "", now=FIXED_NOW)
    assert e.value.code == "NOT_ACTIVE"


# ---- Complete-side ----


def test_complete_requires_assigned_doctor(session, seed):
    appt = make_appointment(session, start=NEXT_WEDNESDAY, patient_id="P01", doctor_id="D1")
    with pytest.raises(PermissionError):
        validate_complete(appt, "doctor", "D2")
    with pytest.raises(PermissionError):
        validate_complete(appt, "patient", "P01")


def test_complete_NOT_ACTIVE(session, seed):
    appt = make_appointment(session, start=NEXT_WEDNESDAY, status="cancelled")
    with pytest.raises(RuleError) as e:
        validate_complete(appt, "doctor", "D1")
    assert e.value.code == "NOT_ACTIVE"
