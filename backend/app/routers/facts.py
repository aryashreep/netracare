"""Fact of the Day endpoint. Fails open with a fixed fallback."""

from fastapi import APIRouter, Query

from app.constants import FACT_CAVEAT, FACT_FALLBACK
from app.llm import FactUnavailable, generate_fact
from app.schemas import FactResponse

router = APIRouter(tags=["facts"])


@router.get("/fact-of-the-day", response_model=FactResponse)
def fact_of_the_day(previous: str | None = Query(default=None)) -> FactResponse:
    try:
        text = generate_fact(previous)
    except FactUnavailable:
        text = FACT_FALLBACK
    return FactResponse(fact=text, caveat=FACT_CAVEAT)
