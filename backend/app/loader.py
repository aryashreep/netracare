"""
Idempotent CSV loader. Reads from settings.data_dir and inserts rows into empty tables.
Called once at application startup via the main.py lifespan.
"""

import csv
from datetime import date
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.models import Doctor, Holiday, Patient, WeeklyScheduleEntry

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

    session.commit()
    return counts
