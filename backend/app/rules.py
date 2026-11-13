"""
Rules engine. The single authority for whether a booking / cancel / complete is allowed.

No FastAPI imports — callers inject the DB session and `now`. This lets the stretch-goal
harness replay the 38 cases against `CLINIC_NOW=2026-11-02T10:00:00` deterministically
(constitution Principle V).

The 17 canonical reason codes raised here are the public contract. See
`docs/conventions.md` §2.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlmodel import Session, select

from app.errors import RuleError
from app.models import Appointment, Doctor, Holiday, WeeklyScheduleEntry

# Session windows. Lunch 13:00–14:00 is dead time.
AM_START = time(9, 0)
AM_END = time(13, 0)
PM_START = time(14, 0)
PM_END = time(18, 0)

DURATIONS = {"new": timedelta(minutes=20), "follow_up": timedelta(minutes=10)}


def _session_for(t: time) -> str | None:
    """Return 'AM' / 'PM' / None depending on which session `t` starts in."""
    if AM_START <= t < AM_END:
        return "AM"
    if PM_START <= t < PM_END:
        return "PM"
    return None


def _session_end(session: str) -> time:
    return AM_END if session == "AM" else PM_END


def validate_booking(
    doctor_id: str,
    patient_id: str,
    speciality: str,
    visit_type: str,
    start_ts: datetime,
    *,
    session: Session,
    now: datetime,
) -> datetime:
    """Raise RuleError on refusal; return the computed end_ts on success."""

    # 1. Start must be on a 10-minute mark.
    if start_ts.minute % 10 != 0 or start_ts.second != 0 or start_ts.microsecond != 0:
        raise RuleError("INVALID_START_TIME")

    # 2/3. Time window.
    if start_ts <= now:
        raise RuleError("IN_PAST")
    if start_ts > now + timedelta(days=30):
        raise RuleError("BEYOND_30_DAYS")

    # 4. Sunday = clinic closed.
    if start_ts.weekday() == 6:
        raise RuleError("CLINIC_CLOSED")

    # 5. Holiday.
    if session.get(Holiday, start_ts.date()) is not None:
        raise RuleError("HOLIDAY")

    # 6. Must fall inside one of the two sessions.
    am_or_pm = _session_for(start_ts.time())
    if am_or_pm is None:
        raise RuleError("OUTSIDE_SESSION")

    # 7. End must not spill past that session.
    duration = DURATIONS.get(visit_type)
    if duration is None:
        raise RuleError("INVALID_START_TIME")  # unknown visit_type treated as malformed
    end_ts = start_ts + duration
    if end_ts.time() > _session_end(am_or_pm):
        raise RuleError("ENDS_AFTER_SESSION")

    # 8. Doctor's schedule for this (weekday, session).
    schedule = session.exec(
        select(WeeklyScheduleEntry).where(
            WeeklyScheduleEntry.doctor_id == doctor_id,
            WeeklyScheduleEntry.weekday == start_ts.weekday(),
            WeeklyScheduleEntry.session == am_or_pm,
        )
    ).first()
    if schedule is None or schedule.status == "OFF":
        raise RuleError("DOCTOR_OFF")
    if schedule.status == "SURGERY":
        raise RuleError("SURGERY_SESSION")

    # 9. Doctor must cover the speciality.
    doctor = session.get(Doctor, doctor_id)
    if doctor is None:
        raise RuleError("DOCTOR_OFF")  # unknown doctor collapses to "not available"
    specs = {s.strip() for s in doctor.specialities.split(";")}
    if speciality not in specs:
        raise RuleError("SPECIALITY_MISMATCH")

    # 10. No overlap with any other booked appointment for this doctor.
    overlapping = session.exec(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status == "booked",
            Appointment.start_ts < end_ts,
            Appointment.end_ts > start_ts,
        )
    ).first()
    if overlapping is not None:
        raise RuleError("DOUBLE_BOOKED")

    # 11. One active booking per (patient, speciality).
    active = session.exec(
        select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.speciality == speciality,
            Appointment.status == "booked",
        )
    ).first()
    if active is not None:
        raise RuleError("ACTIVE_BOOKING_EXISTS")

    # 12. Follow-up rules.
    if visit_type == "follow_up":
        last_completed = session.exec(
            select(Appointment)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.speciality == speciality,
                Appointment.status == "completed",
            )
            .order_by(Appointment.end_ts.desc())  # type: ignore[union-attr]
        ).first()
        if last_completed is None:
            raise RuleError("NO_PREVIOUS_VISIT")
        if last_completed.doctor_id != doctor_id:
            raise RuleError("FOLLOW_UP_DIFFERENT_DOCTOR")

    return end_ts


def validate_cancel(
    appointment: Appointment,
    actor_role: str,
    actor_id: str,
    *,
    now: datetime,
) -> None:
    """Raise RuleError on refusal; raise PermissionError on cross-patient access."""

    if appointment.status != "booked":
        raise RuleError("NOT_ACTIVE")

    if actor_role == "patient":
        if appointment.patient_id != actor_id:
            raise PermissionError("That appointment belongs to another patient.")
        if appointment.start_ts - now < timedelta(hours=2):
            raise RuleError("INSIDE_2_HOURS")
    elif actor_role == "staff":
        pass  # Staff can always cancel.
    elif actor_role == "doctor":
        raise PermissionError("Doctors cannot cancel appointments directly.")


def validate_complete(appointment: Appointment, actor_role: str, actor_id: str) -> None:
    """Raise RuleError/PermissionError on refusal."""

    if actor_role != "doctor" or appointment.doctor_id != actor_id:
        raise PermissionError("Only the assigned doctor can complete this appointment.")
    if appointment.status != "booked":
        raise RuleError("NOT_ACTIVE")
