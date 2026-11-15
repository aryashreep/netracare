"""Urgent-case endpoints. Staff only."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.auth import Actor, current_actor
from app.clock import now as clock_now
from app.db import get_session
from app.models import Patient, UrgentCase
from app.schemas import (
    UrgentCaseList,
    UrgentCasePatient,
    UrgentCaseRead,
    UrgentCaseSeen,
)

router = APIRouter(tags=["urgent"])


def _require_staff(actor: Actor) -> None:
    if actor.role != "staff":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff only")


def _read(case: UrgentCase, session: Session) -> UrgentCaseRead:
    patient = session.get(Patient, case.patient_id)
    return UrgentCaseRead(
        id=case.id,  # type: ignore[arg-type]
        patient=UrgentCasePatient(id=patient.id, name=patient.name),
        appointment_id=case.appointment_id,
        reason_text=case.reason_text,
        category=case.category,
        why=case.why,
        created_at=case.created_at,
        seen_at=case.seen_at,
    )


@router.get("/urgent-cases", response_model=UrgentCaseList)
def list_urgent_cases(
    include_seen: bool = Query(default=False),
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> UrgentCaseList:
    _require_staff(actor)
    stmt = select(UrgentCase)
    if not include_seen:
        stmt = stmt.where(UrgentCase.seen_at.is_(None))  # type: ignore[attr-defined]
    stmt = stmt.order_by(UrgentCase.created_at.desc())  # type: ignore[attr-defined]
    rows = session.exec(stmt).all()
    return UrgentCaseList(cases=[_read(c, session) for c in rows])


@router.post("/urgent-cases/{case_id}/seen", response_model=UrgentCaseSeen)
def mark_urgent_case_seen(
    case_id: int,
    actor: Actor = Depends(current_actor),
    session: Session = Depends(get_session),
) -> UrgentCaseSeen:
    _require_staff(actor)
    case = session.get(UrgentCase, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Urgent case not found")
    if case.seen_at is None:
        case.seen_at = clock_now()
        session.add(case)
        session.commit()
        session.refresh(case)
    # Idempotent: a second call returns the existing seen_at unchanged.
    seen_at_val: datetime = case.seen_at  # type: ignore[assignment]
    return UrgentCaseSeen(id=case.id, seen_at=seen_at_val)  # type: ignore[arg-type]
