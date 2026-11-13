from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.clock import now as clock_now
from app.db import get_session
from app.schemas import SlotsResponse
from app.slots import free_slots

router = APIRouter(tags=["slots"])


@router.get("/slots", response_model=SlotsResponse)
def get_slots(
    doctor_id: str = Query(...),
    on_date: date = Query(..., alias="date"),
    visit_type: str = Query(...),
    session: Session = Depends(get_session),
) -> SlotsResponse:
    slots = free_slots(doctor_id, on_date, visit_type, session=session, now=clock_now())
    return SlotsResponse(
        doctor_id=doctor_id,
        date=on_date,
        visit_type=visit_type,
        slots=slots,
    )
