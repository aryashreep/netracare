"""
Shared fixtures. All tests run against an in-memory SQLite DB with a fixed clock
(2026-11-02 10:00 — a Monday), so rule logic is deterministic.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Must be set before any app imports that use settings.
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["DATA_DIR"] = "/tmp/data-pack-01"  # tests don't invoke the loader
os.environ["CLINIC_NOW"] = "2026-11-02T10:00:00"

from app.auth import Actor, issue_token  # noqa: E402
from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Appointment, Doctor, Holiday, Patient, WeeklyScheduleEntry  # noqa: E402

FIXED_NOW = datetime(2026, 11, 2, 10, 0, 0)  # Monday


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def now() -> datetime:
    return FIXED_NOW


@pytest.fixture
def seed(session: Session) -> dict[str, object]:
    """Minimal clinic:
    - Dr. Rao (D1): Cataract, General. Mon–Wed/Fri/Sat all OPD; Thu AM SURGERY, Thu PM OPD.
    - Dr. Iyer (D2): Glaucoma, Cataract. Thu OFF.
    - Dr. Khan (D4): Cornea. All OPD.
    - Patient P01 Asha Verma, P02 Rohan Gupta.
    - Diwali holiday 2026-11-09.
    """
    docs = [
        Doctor(id="D1", name="Dr. Anand Rao", specialities="Cataract;General"),
        Doctor(id="D2", name="Dr. Meera Iyer", specialities="Glaucoma;Cataract"),
        Doctor(id="D4", name="Dr. Fatima Khan", specialities="Cornea;Refractive"),
    ]
    for d in docs:
        session.add(d)

    schedule: list[tuple[str, int, str, str]] = []
    for weekday in range(6):  # Mon..Sat
        for ses in ("AM", "PM"):
            # D1 — Thu AM is SURGERY; rest OPD
            d1_status = "SURGERY" if (weekday == 3 and ses == "AM") else "OPD"
            schedule.append(("D1", weekday, ses, d1_status))
            # D2 — Thu OFF, rest OPD
            d2_status = "OFF" if weekday == 3 else "OPD"
            schedule.append(("D2", weekday, ses, d2_status))
            # D4 — all OPD
            schedule.append(("D4", weekday, ses, "OPD"))
    for doc_id, w, ses, st in schedule:
        session.add(WeeklyScheduleEntry(doctor_id=doc_id, weekday=w, session=ses, status=st))

    session.add(Holiday(date=date(2026, 11, 9), name="Diwali week"))

    session.add(Patient(id="P01", mobile="9000000001", name="Asha Verma", year_of_birth=1958))
    session.add(Patient(id="P02", mobile="9000000002", name="Rohan Gupta", year_of_birth=1985))

    session.commit()
    return {}


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """FastAPI client with the in-memory session wired in."""

    def _get_session_override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# Helper for tests that need a pre-made token without hitting /login.
@pytest.fixture
def patient_token() -> str:
    return issue_token(Actor(role="patient", id="P01"))


@pytest.fixture
def other_patient_token() -> str:
    return issue_token(Actor(role="patient", id="P02"))


@pytest.fixture
def staff_token() -> str:
    return issue_token(Actor(role="staff", id=""))


@pytest.fixture
def doctor_d1_token() -> str:
    return issue_token(Actor(role="doctor", id="D1"))


@pytest.fixture
def doctor_d2_token() -> str:
    return issue_token(Actor(role="doctor", id="D2"))


# Shared factories.


def make_appointment(
    session: Session,
    *,
    patient_id: str = "P01",
    doctor_id: str = "D1",
    speciality: str = "Cataract",
    visit_type: str = "new",
    start: datetime,
    status: str = "booked",
    created_by_role: str = "patient",
) -> Appointment:
    duration = 20 if visit_type == "new" else 10
    appt = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        speciality=speciality,
        visit_type=visit_type,
        start_ts=start,
        end_ts=datetime.fromtimestamp(start.timestamp() + duration * 60),
        status=status,
        created_by_role=created_by_role,
        created_at=FIXED_NOW,
    )
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt
