from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import Actor, issue_token
from app.db import get_session
from app.models import Doctor, Patient
from app.schemas import DoctorLogin, LoginResponse, PatientLogin, StaffLogin

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: PatientLogin | StaffLogin | DoctorLogin = Body(...),
    session: Session = Depends(get_session),
) -> LoginResponse:
    if isinstance(body, PatientLogin):
        patient = session.exec(select(Patient).where(Patient.mobile == body.mobile)).first()
        if patient is None:
            # Unknown mobile creates a new patient. ID scheme: "WALK-<N>".
            existing_walkins = session.exec(
                select(Patient).where(Patient.id.like("WALK-%"))  # type: ignore[union-attr]
            ).all()
            next_n = len(existing_walkins) + 1
            patient = Patient(id=f"WALK-{next_n}", mobile=body.mobile, name=body.name)
            session.add(patient)
            session.commit()
            session.refresh(patient)
        actor = Actor(role="patient", id=patient.id)

    elif isinstance(body, StaffLogin):
        actor = Actor(role="staff", id="")

    elif isinstance(body, DoctorLogin):
        doctor = session.get(Doctor, body.doctor_id)
        if doctor is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Doctor {body.doctor_id} not found")
        actor = Actor(role="doctor", id=doctor.id)

    else:  # pragma: no cover
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid login body")

    token = issue_token(actor)
    return LoginResponse(token=token, role=actor.role, id=actor.id)
