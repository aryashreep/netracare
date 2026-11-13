from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app import rules
from app.auth import Actor, current_actor
from app.clock import now as clock_now
from app.db import get_session
from app.models import Appointment, Doctor, Patient
from app.schemas import (
    AppointmentCreate,
    AppointmentDoctorInfo,
    AppointmentPatientInfo,
    AppointmentRead,
    StatusResponse,
)

router = APIRouter(tags=["appointments"])


def _read(appt: Appointment, session: Session) -> AppointmentRead:
    patient = session.get(Patient, appt.patient_id)
    doctor = session.get(Doctor, appt.doctor_id)
    return AppointmentRead(
        id=appt.id,  # type: ignore[arg-type]
        patient=AppointmentPatientInfo(id=patient.id, name=patient.name),
        doctor=AppointmentDoctorInfo(id=doctor.id, name=doctor.name),
        speciality=appt.speciality,
        visit_type=appt.visit_type,
        start_ts=appt.start_ts,
        end_ts=appt.end_ts,
        status=appt.status,
    )


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

    now = clock_now()
    end_ts = rules.validate_booking(
        doctor_id=body.doctor_id,
        patient_id=patient_id,
        speciality=body.speciality,
        visit_type=body.visit_type,
        start_ts=body.start_ts,
        session=session,
        now=now,
    )
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
    )
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return _read(appt, session)


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
    return [_read(a, session) for a in session.exec(stmt).all()]


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
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> StatusResponse:
    appt = session.get(Appointment, appt_id)
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    rules.validate_complete(appt, actor.role, actor.id)
    appt.status = "completed"
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return StatusResponse(id=appt.id, status=appt.status)  # type: ignore[arg-type]
