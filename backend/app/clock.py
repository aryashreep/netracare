from datetime import date, datetime

from app.config import settings


def now() -> datetime:
    frozen = settings.frozen_now()
    return frozen if frozen is not None else datetime.now()


def today() -> date:
    return now().date()
