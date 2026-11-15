from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app import rules
from app.auth import Actor, current_actor
from app.clock import now as clock_now
from app.constants import EMERGENCY_MESSAGE
from app.db import get_session
from app.errors import RuleError
from app.llm import RedFlagCheckError, check_red_flags
from app.models import Appointment, Doctor, Patient, UrgentCase
from app.schemas import (
    AppointmentComplete,
    AppointmentCreate,
    AppointmentDoctorInfo,
    AppointmentPatientInfo,
    AppointmentRead,
    RedFlagInfo,
    StatusResponse,
)

router = APIRouter(tags=["appointments"])

_MAX_REASON_CHARS = 300


def _has_open_urgent(session: Session, appt_id: int | None) -> bool:
    if appt_id is None:
        return False
    row = session.exec(
        select(UrgentCase).where(UrgentCase.appointment_id == appt_id)
    ).first()
    return row is not None


def _read(
    appt: Appointment,
    session: Session,
    *,
    actor: Actor,
    red_flag: RedFlagInfo | None = None,
) -> AppointmentRead:
    patient = session.get(Patient, appt.patient_id)
    doctor = session.get(Doctor, appt.doctor_id)
    # Role-scoped field disclosure:
    #   - patient sees own reason, not doctor_note (clinical content)
    #   - doctor sees reason + note on their own appointments
    #   - staff sees both on every appointment
    can_see_reason = (
        actor.role == "staff"
        or (actor.role == "patient" and appt.patient_id == actor.id)
        or (actor.role == "doctor" and appt.doctor_id == actor.id)
    )
    can_see_note = actor.role == "staff" or (
        actor.role == "doctor" and appt.doctor_id == actor.id
    )
    return AppointmentRead(
        id=appt.id,  # type: ignore[arg-type]
        patient=AppointmentPatientInfo(id=patient.id, name=patient.name),
        doctor=AppointmentDoctorInfo(id=doctor.id, name=doctor.name),
        speciality=appt.speciality,
        visit_type=appt.visit_type,
        start_ts=appt.start_ts,
        end_ts=appt.end_ts,
        status=appt.status,
        reason=appt.reason if can_see_reason else None,
        doctor_note=appt.doctor_note if can_see_note else None,
        urgent=_has_open_urgent(session, appt.id),
        red_flag=red_flag,
    )


def _validate_reason(reason: str) -> str:
    """Enforce the 1..300 char rule with canonical reason codes."""
    cleaned = (reason or "").strip()
    if not cleaned:
        raise RuleError("REASON_REQUIRED")
    if len(cleaned) > _MAX_REASON_CHARS:
        raise RuleError("REASON_TOO_LONG")
    return cleaned


@router.post("/appointments", response_model=AppointmentRead, status_code=201)
def create_appointment(
    body: AppointmentCreate,
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> AppointmentRead:
    if actor.role == "patient":
        patient_id = actor.id
    elif actor.role == "staff":
        if not body.patient_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Staff bookings require patient_id"
            )
        if session.get(Patient, body.patient_id) is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Patient {body.patient_id} not found"
            )
        patient_id = body.patient_id
    else:  # doctor
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Doctors cannot create bookings")

    # 1. Shape validation (REASON_REQUIRED / REASON_TOO_LONG).
    reason_text = _validate_reason(body.reason)

    # 2. Red-flag pre-check. Fails CLOSED on any error.
    try:
        rf = check_red_flags(reason_text)
    except RedFlagCheckError as exc:
        # Fail-closed: no appointment, no urgent case, 503 refusal.
        raise RuleError("RED_FLAG_CHECK_UNAVAILABLE") from exc

    now = clock_now()
    red_flag_info: RedFlagInfo | None = None
    urgent_case: UrgentCase | None = None

    if rf.red_flag and rf.category:
        red_flag_info = RedFlagInfo(
            category=rf.category,
            why=rf.why,
            emergency_message=EMERGENCY_MESSAGE,
        )
        # Persist the urgent case BEFORE the rules check so it survives a
        # subsequent booking refusal (spec FR-014).
        urgent_case = UrgentCase(
            patient_id=patient_id,
            appointment_id=None,
            reason_text=reason_text,
            category=rf.category,
            why=rf.why,
            created_at=now,
        )
        session.add(urgent_case)
        session.commit()
        session.refresh(urgent_case)

    # 3. Clinic-rule validation (Iter 1, untouched).
    try:
        end_ts = rules.validate_booking(
            doctor_id=body.doctor_id,
            patient_id=patient_id,
            speciality=body.speciality,
            visit_type=body.visit_type,
            start_ts=body.start_ts,
            session=session,
            now=now,
        )
    except RuleError as exc:
        # Carry the red flag through on the refusal payload too.
        if red_flag_info is not None:
            exc.message = f"{exc.message}"  # unchanged; the handler reads code/message
            # Attach as a dynamic attribute for the exception handler to read.
            setattr(exc, "red_flag", red_flag_info.model_dump())
        raise

    appt = Appointment(
        patient_id=patient_id,
        doctor_id=body.doctor_id,
        speciality=body.speciality,
        visit_type=body.visit_type,
        start_ts=body.start_ts,
        end_ts=end_ts,
        status="booked",
        created_by_role=actor.role,
        created_at=now,
        reason=reason_text,
        doctor_note=None,
    )
    session.add(appt)
    session.commit()
    session.refresh(appt)

    # Link the urgent case to the booked appointment now that we have an id.
    if urgent_case is not None:
        urgent_case.appointment_id = appt.id
        session.add(urgent_case)
        session.commit()

    return _read(appt, session, actor=actor, red_flag=red_flag_info)


@router.get("/appointments", response_model=list[AppointmentRead])
def list_appointments(
    appt_status: str | None = Query(default=None, alias="status"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    doctor_id: str | None = Query(default=None),
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> list[AppointmentRead]:
    stmt = select(Appointment)
    if actor.role == "patient":
        stmt = stmt.where(Appointment.patient_id == actor.id)
    elif actor.role == "doctor":
        stmt = stmt.where(Appointment.doctor_id == actor.id)
    # staff: no filter
    if appt_status:
        stmt = stmt.where(Appointment.status == appt_status)
    if from_date:
        stmt = stmt.where(Appointment.start_ts >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        stmt = stmt.where(Appointment.start_ts < datetime.combine(to_date, datetime.max.time()))
    if doctor_id and actor.role == "staff":
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    stmt = stmt.order_by(Appointment.start_ts)  # type: ignore[arg-type]
    return [_read(a, session, actor=actor) for a in session.exec(stmt).all()]


@router.post("/appointments/{appt_id}/cancel", response_model=StatusResponse)
def cancel_appointment(
    appt_id: int,
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> StatusResponse:
    appt = session.get(Appointment, appt_id)
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    rules.validate_cancel(appt, actor.role, actor.id, now=clock_now())
    appt.status = "cancelled"
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return StatusResponse(id=appt.id, status=appt.status)  # type: ignore[arg-type]


@router.post("/appointments/{appt_id}/complete", response_model=StatusResponse)
def complete_appointment(
    appt_id: int,
    body: AppointmentComplete,
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> StatusResponse:
    appt = session.get(Appointment, appt_id)
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    note = (body.doctor_note or "").strip()
    if not note:
        raise RuleError("NOTE_REQUIRED")
    rules.validate_complete(appt, actor.role, actor.id)
    appt.status = "completed"
    appt.doctor_note = note
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return StatusResponse(id=appt.id, status=appt.status)  # type: ignore[arg-type]
