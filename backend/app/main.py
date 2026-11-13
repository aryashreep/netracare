from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.db import create_db_and_tables, engine
from app.errors import REASON_MESSAGES, RuleError
from app.loader import seed
from app.routers import appointments as appointments_router
from app.routers import auth as auth_router
from app.routers import doctors as doctors_router
from app.routers import slots as slots_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        counts = seed(session)
    if counts:
        print(f"Seed loaded: {counts}")
    yield


app = FastAPI(title="NetraCare API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RuleError)
async def rule_error_handler(_request: Request, exc: RuleError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"code": exc.code, "message": exc.message})


@app.exception_handler(PermissionError)
async def permission_error_handler(_request: Request, exc: PermissionError) -> JSONResponse:
    message = str(exc) or REASON_MESSAGES["NOT_YOUR_APPOINTMENT"]
    return JSONResponse(
        status_code=403, content={"code": "NOT_YOUR_APPOINTMENT", "message": message}
    )


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router.router)
app.include_router(doctors_router.router)
app.include_router(slots_router.router)
app.include_router(appointments_router.router)
