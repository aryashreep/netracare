from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# SQLite (used by the pytest fixtures) needs check_same_thread=False when shared
# across threads; Postgres doesn't. pool_pre_ping shields us from Postgres connections
# dropped by restarts or long idle periods.
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=False,
    )


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
