"""
Pydantic DTOs — kept separate from SQLModel DB models (plan.md D2).
Request/response shapes for every endpoint in contracts/api.md.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---- Login ----


class PatientLogin(BaseModel):
    role: Literal["patient"]
    mobile: str
    name: str


class StaffLogin(BaseModel):
    role: Literal["staff"]
    name: str


class DoctorLogin(BaseModel):
    role: Literal["doctor"]
    doctor_id: str


class LoginResponse(BaseModel):
    token: str
    role: str
    id: str


# ---- Doctors ----


class DoctorRead(BaseModel):
    id: str
    name: str
    specialities: list[str]


# ---- Slots ----


class SlotsResponse(BaseModel):
    doctor_id: str
    date: date
    visit_type: str
    slots: list[datetime]


# ---- Appointments ----


class AppointmentCreate(BaseModel):
    doctor_id: str
    speciality: str
    visit_type: Literal["new", "follow_up"]
    start_ts: datetime
    patient_id: str | None = None  # Required for staff; ignored for patient role


class AppointmentPatientInfo(BaseModel):
    id: str
    name: str


class AppointmentDoctorInfo(BaseModel):
    id: str
    name: str


class AppointmentRead(BaseModel):
    id: int
    patient: AppointmentPatientInfo
    doctor: AppointmentDoctorInfo
    speciality: str
    visit_type: str
    start_ts: datetime
    end_ts: datetime
    status: str


class StatusResponse(BaseModel):
    id: int
    status: str


# ---- Refusals ----


class Refusal(BaseModel):
    code: str = Field(..., description="One of the 17 canonical reason codes.")
    message: str
