# Implementation Plan: Clinic Booking Foundation

**Branch**: `iteration-1` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-clinic-booking-foundation/spec.md`

## Summary

Build the foundational NetraCare clinic-booking web application: a FastAPI service backed
by SQLite that enforces every clinic rule in one place, a Next.js front-end for three
roles (Patient, Staff, Doctor), and a Docker Compose dev loop. No AI yet — every piece of
this plan is a durable contract that Iterations 2–6 extend without re-writing. The rules
engine and slot-computation modules are pure functions that take `now` as a parameter so
the stretch-goal 38-case rule harness (`CLINIC_NOW=2026-11-02T10:00:00`) can replay
deterministically. The 17 canonical `reason_code` values from the data pack README are
the public refusal contract.

## Technical Context

**Language/Version:** Python 3.11+ (backend), TypeScript 5.x (frontend).

**Primary Dependencies:** FastAPI, SQLModel, Pydantic v2, `python-dotenv` (backend);
Next.js 14 (App Router), React 18, Tailwind CSS 3, `swr` for client-side fetching
(frontend). `uvicorn` for the ASGI server, `pnpm` for frontend package management.

**Storage:** SQLite on disk, file at `/app/data/netracare.db` inside the backend
container, host-mounted from `./data/`. Managed through SQLModel's session API.

**Testing:** `pytest` + `httpx` for backend API tests. One `tests/rules/` module exercises
the pure rule functions directly against the fixed-clock harness (`stretch/rule_tests.csv`,
38 cases). Manual verification against the brief's §09 table for end-to-end. Frontend
tests deferred.

**Target Platform:** Linux containers orchestrated by Docker Compose; dev machine macOS or
Linux. Backend exposes `:8000`, frontend `:3000`.

**Project Type:** Web application — separate `backend/` and `frontend/` services.

**Performance Goals:** Classroom scale. `GET /slots` under 100 ms for a single-doctor
day; booking endpoints under 200 ms p95. Not a concern at current data volumes.

**Constraints:** Must run on macOS and Linux via `docker compose up` with no extra steps.
SQLite file lives in the host-mounted `./data/` volume so it survives container restarts.
Fixed-clock support via `CLINIC_NOW` env var (read once at request time; never read system
clock from inside `rules.py` or `slots.py`).

**Scale/Scope:** 5 doctors, 25 seed patients, ~6 OPD half-days × 24 slots per doctor ≈
720 bookable slots per week. Realistic weekly appointment count in the low hundreds.

## Constitution Check

*Gate — must pass before Phase 0.* Re-checked after Phase 1.

| Principle | Status | Evidence |
|---|---|---|
| I. Safety is a Backend Invariant | ✅ Pass | `backend/app/rules.py` is the sole validator; every booking/cancel path calls `validate_booking` / `validate_cancel`. Frontend displays refusals only. |
| II. Clinic Never Gives Medical Advice | ✅ Pass (trivially) | No LLM in this iteration. No patient-facing generative text. Red-flag check arrives Iter 2 before the first booking goes through it. |
| III. Data Boundaries | ✅ Pass | `auth.current_actor()` dependency gates every endpoint; patient routes filter by `actor.id`. Direct-API cross-patient test is an acceptance scenario (US-4 #2). Only data-pack CSVs are loaded. |
| IV. Spec-Driven Development | ✅ Pass | This plan is the direct output of `/speckit-plan` after `/speckit-specify` produced `spec.md`. `CODEOWNERS` protects `rules.py`, `slots.py`, `constitution.md`, and `specs/`. |
| V. Pure Logic, Deterministic Time, Dockerized | ✅ Pass | `rules.py` and `slots.py` import no FastAPI; they accept `now` and session as parameters. Docker scaffold and `docker-compose.yml` already in place at repo root. `CLINIC_NOW` reserved in `.env.example`. |

**No violations. Complexity Tracking section below is empty, as required.**

## Project Structure

### Documentation (this feature)

```text
specs/001-clinic-booking-foundation/
├── plan.md                      # this file
├── research.md                  # Phase 0 output
├── data-model.md                # Phase 1 output
├── quickstart.md                # Phase 1 output
├── contracts/
│   └── api.md                   # Phase 1 output — endpoint contracts
├── checklists/
│   └── requirements.md          # from /speckit-specify
└── spec.md                      # from /speckit-specify
```

### Source Code (repository root)

```text
backend/
├── Dockerfile
├── .dockerignore
├── pyproject.toml               # fastapi, sqlmodel, pydantic, uvicorn, httpx (test)
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, lifespan startup (seed loader), CORS, router mount
│   ├── config.py                # Settings via pydantic-settings — reads DATABASE_URL, DATA_DIR, CLINIC_NOW
│   ├── clock.py                 # now() — honors CLINIC_NOW if set, else datetime.now()
│   ├── db.py                    # engine, get_session dependency
│   ├── models.py                # Doctor, WeeklyScheduleEntry, Holiday, Patient, Appointment (SQLModel)
│   ├── schemas.py               # Pydantic request/response DTOs distinct from DB models
│   ├── errors.py                # RuleError, reason-code → message map
│   ├── rules.py                 # ⚠ pure — validate_booking, validate_cancel, validate_complete
│   ├── slots.py                 # ⚠ pure — free_slots(doctor_id, date, visit_type, now, session)
│   ├── loader.py                # CSV → DB seed (idempotent; runs on startup if tables empty)
│   ├── auth.py                  # in-memory token store, current_actor() dependency
│   └── routers/
│       ├── __init__.py
│       ├── auth.py              # POST /login
│       ├── doctors.py           # GET /doctors
│       ├── slots.py             # GET /slots
│       ├── appointments.py      # POST/GET /appointments; POST /{id}/cancel; POST /{id}/complete
│       └── staff.py             # GET /staff/appointments (all; filter by doctor/date)
└── tests/
    ├── conftest.py              # test client, in-memory DB, fixed-clock fixture
    ├── test_rules.py            # pure-function tests for every reason code
    ├── test_rule_harness.py     # runs stretch/rule_tests.csv (stretch goal)
    ├── test_slots.py            # free_slots edge cases
    ├── test_auth_scoping.py     # cross-patient access is refused
    └── test_api_bookings.py     # end-to-end booking + cancel flow

frontend/
├── Dockerfile
├── .dockerignore
├── package.json                 # next, react, typescript, tailwind, swr
├── tsconfig.json
├── next.config.mjs
├── tailwind.config.ts
├── app/
│   ├── layout.tsx               # global shell, role-aware navbar
│   ├── page.tsx                 # role picker / login
│   ├── patient/
│   │   ├── page.tsx             # dashboard: upcoming appointments
│   │   └── book/page.tsx        # doctor/specialty/slot picker → POST /appointments
│   ├── staff/
│   │   ├── page.tsx             # all appointments table; filter by doctor/date
│   │   └── book/page.tsx        # walk-in booking (any patient)
│   └── doctor/
│       └── page.tsx             # my-schedule-by-date + "mark completed"
└── lib/
    ├── api.ts                   # typed fetch wrapper; reads token from localStorage; maps 409 → UI
    ├── types.ts                 # TS mirror of backend DTOs
    └── session.ts               # login helpers

data/
├── data-pack-01/                # shipped CSVs — doctors, weekly_schedule, holidays, patients, stretch/
└── netracare.db                 # created at runtime; git-ignored

docker-compose.yml               # backend + frontend services (commented slots for Iter 3+)
docker-compose.override.yml      # dev: source mounts + hot-reload commands
.env                             # local only — git-ignored
.env.example                     # committed — reserves ANTHROPIC_API_KEY (unused Iter 1), CLINIC_NOW
```

**Structure Decision:** Web application (backend + frontend). `backend/` and `frontend/`
are independent build contexts with their own Dockerfile and `.dockerignore`. `data/` is
a host-mounted volume shared with the backend container. The pure modules
(`backend/app/rules.py`, `backend/app/slots.py`) have no FastAPI imports so Iteration 2's
red-flag check and Iteration 4's agent can both call them without circular wiring. The
`backend/app/clock.py` module exists specifically to satisfy Constitution Principle V —
no business logic reads the system clock directly.

## Complexity Tracking

> No constitution violations. Section intentionally empty.
