"""Doctor-only views: the AI summary of a patient's record."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth import Actor, current_actor
from app.clock import now as clock_now
from app.constants import SUMMARY_FALLBACK
from app.db import get_session
from app.errors import RuleError
from app.llm import SummaryUnavailable, summarize_patient
from app.models import Appointment, Doctor, Patient, PatientProfile
from app.schemas import (
    DoctorSummaryResponse,
    PastVisitRead,
    ProfileRead,
)

router = APIRouter(tags=["doctor"])


@router.get(
    "/doctor/patients/{patient_id}/summary", response_model=DoctorSummaryResponse
)
def patient_summary(
    patient_id: str,
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> DoctorSummaryResponse:
    # Doctor-only. Non-doctor callers get the canonical NOT_YOUR_APPOINTMENT.
    if actor.role != "doctor":
        raise RuleError("NOT_YOUR_APPOINTMENT", "Only doctors can read patient summaries.")

    patient = session.get(Patient, patient_id)
    if patient is None:
        raise RuleError("NOT_YOUR_APPOINTMENT", "Patient not found.")

    profile = session.get(PatientProfile, patient_id)
    profile_payload = ProfileRead(
        year_of_birth=patient.year_of_birth,
        general_health=profile.general_health if profile else None,
        allergies=profile.allergies if profile else None,
    )

    # Today's reason: the current booked appointment for this doctor + patient,
    # starting on or after now, closest first.
    today_now = clock_now()
    today_stmt = (
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .where(Appointment.doctor_id == actor.id)
        .where(Appointment.status == "booked")
        .where(Appointment.start_ts >= today_now)
        .order_by(Appointment.start_ts)  # type: ignore[arg-type]
    )
    today_appt = session.exec(today_stmt).first()
    today_reason = today_appt.reason if today_appt and today_appt.reason else None

    # Past completed visits from ALL doctors, newest first (spec FR-021).
    past_stmt = (
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .where(Appointment.status == "completed")
        .order_by(Appointment.start_ts.desc())  # type: ignore[attr-defined]
    )
    past_rows = session.exec(past_stmt).all()

    past_visits_payload: list[PastVisitRead] = []
    doctor_names: dict[str, str] = {}
    for a in past_rows:
        if a.doctor_id not in doctor_names:
            doc = session.get(Doctor, a.doctor_id)
            doctor_names[a.doctor_id] = doc.name if doc else a.doctor_id
        past_visits_payload.append(
            PastVisitRead(
                date=a.start_ts.date().isoformat(),
                doctor_name=doctor_names[a.doctor_id],
                speciality=a.speciality,
                doctor_note=a.doctor_note or "",
            )
        )

    age = _age_from_yob(patient.year_of_birth, today_now)

    # LLM call. Fails OPEN — fallback summary + raw data is still returned.
    try:
        summary = summarize_patient(
            age=age,
            general_health=profile.general_health if profile else None,
            allergies=profile.allergies if profile else None,
            today_reason=today_reason,
            past_visits=[pv.model_dump() for pv in past_visits_payload],
        )
    except SummaryUnavailable:
        summary = SUMMARY_FALLBACK

    return DoctorSummaryResponse(
        summary=summary,
        past_visits=past_visits_payload,
        profile=profile_payload,
    )


def _age_from_yob(yob: int | None, now: datetime) -> int | None:
    if yob is None:
        return None
    return max(0, now.year - yob)
