from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import Doctor
from app.schemas import DoctorRead

router = APIRouter(tags=["doctors"])


@router.get("/doctors", response_model=list[DoctorRead])
def list_doctors(session: Session = Depends(get_session)) -> list[DoctorRead]:
    doctors = session.exec(select(Doctor).order_by(Doctor.id)).all()
    return [
        DoctorRead(id=d.id, name=d.name, specialities=d.specialities.split(";"))
        for d in doctors
    ]
