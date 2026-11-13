from datetime import date as _date
from datetime import datetime
from typing import Literal

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel

# Project-wide convention: appointment timestamps are clinic-local, timezone-naive.
# NaiveDatetime tells SQLModel/Pydantic to accept and store them as naive.
_DT = NaiveDatetime  # type: ignore[assignment]

# Status enums kept as string Literals — SQLite stores plain strings.
VisitType = Literal["new", "follow_up"]
Session = Literal["AM", "PM"]
ScheduleStatus = Literal["OPD", "SURGERY", "OFF"]
AppointmentStatus = Literal["booked", "cancelled", "completed"]
Role = Literal["patient", "staff", "doctor"]


class Doctor(SQLModel, table=True):
    # Uses the CSV's string IDs (e.g. "D1") — no remapping between data pack and app.
    id: str = Field(primary_key=True)
    name: str = Field(index=True, unique=True)
    specialities: str  # Semicolon-separated, matches data pack.


class WeeklyScheduleEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    doctor_id: str = Field(foreign_key="doctor.id", index=True)
    weekday: int  # 0=Mon .. 5=Sat
    session: str  # "AM" or "PM"
    status: str  # "OPD", "SURGERY", "OFF"


class Holiday(SQLModel, table=True):
    date: _date = Field(primary_key=True)
    name: str


class Patient(SQLModel, table=True):
    id: str = Field(primary_key=True)
    mobile: str = Field(index=True, unique=True)
    name: str
    year_of_birth: int | None = None


class Appointment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    doctor_id: str = Field(foreign_key="doctor.id", index=True)
    speciality: str
    visit_type: str  # "new" | "follow_up"
    start_ts: _DT = Field(index=True)
    end_ts: _DT
    status: str = Field(default="booked", index=True)  # "booked" | "cancelled" | "completed"
    created_by_role: str  # "patient" | "staff"
    created_at: _DT
