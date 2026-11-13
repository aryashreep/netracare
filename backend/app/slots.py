"""
Pure free-slot computation. No FastAPI imports.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.models import Appointment, Holiday, WeeklyScheduleEntry
from app.rules import AM_END, AM_START, DURATIONS, PM_END, PM_START


def _session_bounds(session_name: str) -> tuple[datetime.time, datetime.time]:  # type: ignore[name-defined]
    return (AM_START, AM_END) if session_name == "AM" else (PM_START, PM_END)


def free_slots(
    doctor_id: str,
    on_date: date,
    visit_type: str,
    *,
    session: Session,
    now: datetime,
) -> list[datetime]:
    """List 10-minute-aligned bookable start times for (doctor, date, visit_type)."""

    if on_date.weekday() == 6:  # Sunday
        return []
    if session.get(Holiday, on_date) is not None:
        return []
    if on_date < now.date():
        return []

    duration = DURATIONS.get(visit_type)
    if duration is None:
        return []

    out: list[datetime] = []
    schedule_rows = session.exec(
        select(WeeklyScheduleEntry).where(
            WeeklyScheduleEntry.doctor_id == doctor_id,
            WeeklyScheduleEntry.weekday == on_date.weekday(),
        )
    ).all()

    # Overlap set: all booked appointments for this doctor on this date.
    day_start = datetime.combine(on_date, AM_START)
    day_end = datetime.combine(on_date, PM_END)
    existing = session.exec(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status == "booked",
            Appointment.start_ts >= day_start,
            Appointment.start_ts < day_end,
        )
    ).all()

    for row in schedule_rows:
        if row.status != "OPD":
            continue
        start_t, end_t = _session_bounds(row.session)
        t = datetime.combine(on_date, start_t)
        session_end = datetime.combine(on_date, end_t)
        while t + duration <= session_end:
            # Past-time guard for today.
            if t > now and not _overlaps(t, t + duration, existing):
                out.append(t)
            t += timedelta(minutes=10)

    out.sort()
    return out


def _overlaps(start: datetime, end: datetime, existing: list[Appointment]) -> bool:
    for a in existing:
        if a.start_ts < end and a.end_ts > start:
            return True
    return False
