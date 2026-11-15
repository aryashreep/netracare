"""
Idempotent CSV loader. Reads from settings.data_dir and inserts rows into empty tables.
Called once at application startup via the main.py lifespan.
"""

import csv
from datetime import date, datetime
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.models import (
    Appointment,
    Doctor,
    Holiday,
    Patient,
    PatientProfile,
    WeeklyScheduleEntry,
)

_WEEKDAY: dict[str, int] = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed(session: Session) -> dict[str, int]:
    """Populate empty tables from the data pack. Returns row counts.
    Silently no-ops if the data pack is not present (useful for tests)."""

    data_dir = Path(settings.data_dir)
    if not data_dir.exists():
        return {}
    counts: dict[str, int] = {}

    if not session.exec(select(Doctor)).first():
        rows = _read(data_dir / "doctors.csv")
        for r in rows:
            session.add(Doctor(id=r["doctor_id"], name=r["name"], specialities=r["specialities"]))
        counts["doctors"] = len(rows)

    if not session.exec(select(WeeklyScheduleEntry)).first():
        rows = _read(data_dir / "weekly_schedule.csv")
        for r in rows:
            session.add(
                WeeklyScheduleEntry(
                    doctor_id=r["doctor_id"],
                    weekday=_WEEKDAY[r["day"]],
                    session=r["session"],
                    status=r["status"],
                )
            )
        counts["schedule_entries"] = len(rows)

    if not session.exec(select(Holiday)).first():
        rows = _read(data_dir / "holidays.csv")
        for r in rows:
            session.add(Holiday(date=date.fromisoformat(r["date"]), name=r["name"]))
        counts["holidays"] = len(rows)

    if not session.exec(select(Patient)).first():
        rows = _read(data_dir / "patients.csv")
        for r in rows:
            yob = int(r["year_of_birth"]) if r.get("year_of_birth") else None
            session.add(
                Patient(id=r["patient_id"], mobile=r["mobile"], name=r["name"], year_of_birth=yob)
            )
        counts["patients"] = len(rows)

    # --- Data pack 2 (Iter 2): patient profiles and past completed visits ---
    data_dir_02 = Path(settings.data_dir_02)
    if data_dir_02.exists():
        if not session.exec(select(PatientProfile)).first():
            rows = _read(data_dir_02 / "patient_profiles.csv")
            for r in rows:
                session.add(
                    PatientProfile(
                        patient_id=r["patient_id"],
                        general_health=r["general_health"],
                        allergies=r["allergies"],
                    )
                )
            counts["profiles"] = len(rows)

        # Past visits are seeded as completed appointments. The follow-up rule in
        # rules.py reads Appointment.status == "completed" with no awareness of
        # whether the row was seeded or booked through the API.
        if not session.exec(select(Appointment)).first():
            rows = _read(data_dir_02 / "past_visits.csv")
            for r in rows:
                start = datetime.fromisoformat(f"{r['date']}T{r['start_time']}:00")
                end = datetime.fromisoformat(f"{r['date']}T{r['end_time']}:00")
                session.add(
                    Appointment(
                        patient_id=r["patient_id"],
                        doctor_id=r["doctor_id"],
                        speciality=r["speciality"],
                        visit_type=r["visit_type"],
                        start_ts=start,
                        end_ts=end,
                        status="completed",
                        created_by_role="staff",
                        created_at=start,
                        reason=r["reason"],
                        doctor_note=r["doctor_note"],
                    )
                )
            counts["past_visits"] = len(rows)

    session.commit()
    return counts
