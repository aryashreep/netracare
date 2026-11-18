"""
Pydantic DTOs — kept separate from SQLModel DB models (plan.md D2).
Request/response shapes for every endpoint in contracts/api.md.
"""

from datetime import date, datetime
from typing import Any, Literal

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
    # Required (Iter 2 R3); validated at the handler layer so the refusal
    # carries one of the canonical reason codes (REASON_REQUIRED / REASON_TOO_LONG)
    # rather than a generic Pydantic 422.
    reason: str = ""
    patient_id: str | None = None  # Required for staff; ignored for patient role


class AppointmentComplete(BaseModel):
    # Required (Iter 2 R2); same validation strategy as `reason` above.
    doctor_note: str = ""


class RedFlagInfo(BaseModel):
    category: str
    why: str
    emergency_message: str


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
    # Iter 2 additions. `reason` and `doctor_note` are role-scoped at the
    # router layer (patient sees own reason, doctor and staff see reason +
    # note; patient does not see note).
    reason: str | None = None
    doctor_note: str | None = None
    urgent: bool = False
    red_flag: RedFlagInfo | None = None


class StatusResponse(BaseModel):
    id: int
    status: str


# ---- Refusals ----


class Refusal(BaseModel):
    code: str = Field(..., description="One of the 21 canonical reason codes.")
    message: str


# ---- Iter 2: Fact of the Day ----


class FactResponse(BaseModel):
    fact: str
    caveat: str


# ---- Iter 2: Urgent cases ----


class UrgentCasePatient(BaseModel):
    id: str
    name: str


class UrgentCaseRead(BaseModel):
    id: int
    patient: UrgentCasePatient
    appointment_id: int | None
    reason_text: str
    category: str
    why: str
    created_at: datetime
    seen_at: datetime | None


class UrgentCaseList(BaseModel):
    cases: list[UrgentCaseRead]


class UrgentCaseSeen(BaseModel):
    id: int
    seen_at: datetime


# ---- Iter 2: Doctor summary ----


class PastVisitRead(BaseModel):
    date: str
    doctor_name: str
    speciality: str
    doctor_note: str


class ProfileRead(BaseModel):
    year_of_birth: int | None
    general_health: str | None
    allergies: str | None


class DoctorSummaryResponse(BaseModel):
    summary: str
    past_visits: list[PastVisitRead]
    profile: ProfileRead


def to_json_default(value: Any) -> Any:
    """Small helper for constructing summary input payloads."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value
