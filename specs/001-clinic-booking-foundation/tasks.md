---
description: "Clinic Booking Foundation — ordered implementation tasks"
---

# Tasks: Clinic Booking Foundation

**Input**: Design documents from `/specs/001-clinic-booking-foundation/`

**Prerequisites**: plan.md, spec.md (both required). Also uses research.md, data-model.md, contracts/api.md, quickstart.md.

**Tests**: Backend rule tests are explicitly requested by the spec (SC-001 and the stretch
harness depend on them). Frontend tests are NOT included — brief Iter-1 does not require
them and manual browser verification is the acceptance criterion.

**Organization**: Tasks are grouped by user story. Each user story's section is
independently completable and independently testable — Phase 3 (US-1) alone delivers an
MVP that a patient can use.

## Format: `[ID] [P?] [Story] Description`

- `[P]` — can run in parallel with other `[P]` tasks in the same phase (different files, no dependency).
- `[Story]` — which user story (US-1 patient books, US-2 staff manages, US-3 doctor completes, US-4 identity). Shared setup/foundational tasks use `[—]`.
- Every task names a concrete file path.

## Path Conventions (from plan.md)

Web application. Backend at `backend/`, frontend at `frontend/`. See `plan.md` §Project Structure for the full tree.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose:** Initialize the backend and frontend projects so Phase 2 can begin.

- [X] **T001** [—] Create `backend/pyproject.toml` declaring Python 3.11 and deps: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `pydantic-settings`, `python-multipart`, and dev-deps `pytest`, `httpx`, `ruff`. Add `[tool.ruff]` config (line-length 100).
- [X] **T002** [—] Create `backend/app/__init__.py` and empty `backend/app/main.py` with a FastAPI app placeholder so the Docker container has something to boot while Phase 2 runs.
- [X] **T003** [P] [—] Create `frontend/package.json` with Next.js 14, React 18, TypeScript, Tailwind CSS 3, SWR; add scripts `dev`, `build`, `start`, `lint`. Create `frontend/tsconfig.json`, `frontend/next.config.mjs`, `frontend/tailwind.config.ts`, `frontend/postcss.config.mjs`, `frontend/app/globals.css`.
- [X] **T004** [P] [—] Create `frontend/app/layout.tsx` and a stub `frontend/app/page.tsx` ("NetraCare — coming up") so `docker compose up` yields a running frontend immediately.
- [X] **T005** [—] Verify `docker compose build` succeeds for both services from a clean clone. If a Dockerfile step fails, fix only the `COPY`/`RUN` lines; do not restructure the Dockerfiles (they are already set up to no-op gracefully when deps files are absent).

**Checkpoint:** `docker compose up --build` starts both services with placeholder pages. Phase 2 can begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose:** Build the shared backbone every user story depends on: config, clock, DB, models, loader, errors, auth, routing skeleton, and the pure rule/slot module *skeletons* (not the rule logic itself — that is Phase 3 since it drives the MVP).

**⚠️ CRITICAL:** No user-story work begins until this phase completes.

### Config, clock, DB

- [X] **T006** [—] Create `backend/app/config.py` using `pydantic-settings`: read `DATABASE_URL`, `DATA_DIR`, `CLINIC_NOW` (optional ISO datetime). Export `settings` singleton.
- [X] **T007** [—] Create `backend/app/clock.py` with `now() -> datetime`: returns `datetime.fromisoformat(settings.CLINIC_NOW)` if set, else `datetime.now()`. Also export `today()`. No other module reads the clock directly (Constitution V).
- [X] **T008** [—] Create `backend/app/db.py`: SQLModel engine from `settings.DATABASE_URL`, `create_db_and_tables()`, and a `get_session()` FastAPI dependency.

### Models and loader

- [X] **T009** [P] [—] Create `backend/app/models.py` with all five SQLModel classes per `data-model.md`: `Doctor`, `WeeklyScheduleEntry`, `Holiday`, `Patient`, `Appointment`. Add indexes: `(doctor_id, start_ts)`, `(patient_id, speciality, status)`, `(patient_id, status)`. Appointment has a `created_by_role` string column.
- [X] **T010** [—] Create `backend/app/loader.py`: idempotent CSV loader. Reads from `settings.DATA_DIR` (`data-pack-01/*.csv`). Normalises the schedule CSV so `status` values match `OPD` / `SURGERY` / `OFF`. Called from `main.py` lifespan after `create_db_and_tables()`.

### Errors and reason codes

- [X] **T011** [P] [—] Create `backend/app/errors.py`: `RuleError(Exception)` with `code: str`, `message: str`. A module-level dict `REASON_MESSAGES: dict[str, str]` carrying the human-readable message for each of the 17 canonical codes.
- [X] **T012** [—] In `backend/app/main.py`, register a FastAPI `exception_handler` for `RuleError` → HTTP 409 with `{code, message}`. Register a handler for `PermissionError` → HTTP 403 with `{code: "NOT_YOUR_APPOINTMENT", message}`. Enable permissive CORS for `http://localhost:3000`.

### Auth

- [X] **T013** [—] Create `backend/app/auth.py`: in-memory `_tokens: dict[str, Actor]`. `Actor = NamedTuple(role, id)`. `issue_token(actor) -> str`. `current_actor` FastAPI dependency that reads `Authorization: Bearer ...` and returns `Actor`, raising `HTTPException(401)` on missing/invalid token.
- [X] **T014** [—] Create `backend/app/routers/auth.py` and wire `POST /login`:
  - `role: patient` → look up by mobile; create if unknown; return `{token, role, id}`.
  - `role: doctor` → verify `doctor_id` exists; return token.
  - `role: staff` → accept any `name`; token carries `id=0`.
- [X] **T015** [—] Create `backend/app/routers/doctors.py` with `GET /doctors` (public). Mount both routers in `main.py`.

### Pure module skeletons

- [X] **T016** [P] [—] Create `backend/app/rules.py` with function signatures only: `validate_booking(req, session, *, now)`, `validate_cancel(appt, actor, *, now)`, `validate_complete(appt, actor)`. Each raises `NotImplementedError` for now. **No FastAPI imports.**
- [X] **T017** [P] [—] Create `backend/app/slots.py` with `free_slots(doctor_id, date, visit_type, *, session, now) -> list[datetime]` returning `[]`. **No FastAPI imports.**

### Shared DTOs

- [X] **T018** [—] Create `backend/app/schemas.py`: Pydantic DTOs for login request/response, DoctorRead, SlotsResponse, AppointmentCreate, AppointmentRead. Keep DB models (`models.py`) and API models (`schemas.py`) separate per D2.

**Checkpoint:** `docker compose up`, then `POST /login` with Asha Verma returns a token and `GET /doctors` returns the 5 seeded doctors. All user stories can start in parallel.

---

## Phase 3: User Story 1 — Patient books an eye appointment (Priority: P1) 🎯 MVP

**Goal:** A logged-in patient can see free slots, book a 20-minute new consultation or a
10-minute follow-up, see their own upcoming appointments, and cancel them subject to the
2-hour rule. Every rule-breaking booking is refused with the right `reason_code`.

**Independent Test:** Follow `quickstart.md` §2–§4 as patient Asha Verma (9000000001) and
walk the 13-row verification table from `spec.md` User Story 1.

This phase also folds in **User Story 4** (identity scoping) — the backend tests for
cross-patient access can only be written once appointment endpoints exist.

### Rule engine (the MVP's heart)

- [X] **T019** [US1] Implement `validate_booking` in `backend/app/rules.py`. Ordered checks per `data-model.md`:
  1. `INVALID_START_TIME` — minute %10 != 0
  2. `IN_PAST` — `start_ts <= now`
  3. `BEYOND_30_DAYS` — `start_ts > now + 30d`
  4. `CLINIC_CLOSED` — Sunday (weekday 6)
  5. `HOLIDAY` — date in `Holiday` table
  6. `OUTSIDE_SESSION` — start_ts not in [09:00,13:00) or [14:00,18:00)
  7. `ENDS_AFTER_SESSION` — end_ts outside the same session
  8. Load `WeeklyScheduleEntry(doctor, weekday, session)`:
     - missing or `OFF` → `DOCTOR_OFF`
     - `SURGERY` → `SURGERY_SESSION`
  9. `SPECIALITY_MISMATCH` — speciality not in doctor's semicolon-split list
  10. `DOUBLE_BOOKED` — overlap with any `booked` appointment for this doctor
  11. `ACTIVE_BOOKING_EXISTS` — patient already has a `booked` in this speciality
  12. If follow-up: `NO_PREVIOUS_VISIT` / `FOLLOW_UP_DIFFERENT_DOCTOR` per data-model.md
- [X] **T020** [US1] Implement `validate_cancel` in `rules.py`: `NOT_ACTIVE` if status != booked; `INSIDE_2_HOURS` if actor.role == "patient" and start_ts - now < 2h.
- [X] **T021** [US1] Implement `free_slots` in `backend/app/slots.py`: generate 10-min-aligned candidate starts across OPD sessions on the target date, drop ones whose `end_ts` would exit the session, drop ones that overlap existing `booked` appointments. Returns `[]` on Sundays / holidays / past dates / non-OPD sessions.

### Backend tests (rule engine is load-bearing — tests requested by SC-001)

- [X] **T022** [P] [US1] Create `backend/tests/conftest.py`: in-memory SQLite session fixture, fixed-clock fixture, factory helpers for Doctor/Patient/Schedule/Appointment.
- [X] **T023** [P] [US1] Create `backend/tests/test_rules.py` with one test per reason code (17 tests). Each test constructs just enough data to trigger that specific code and asserts `RuleError.code == "..."`.
- [X] **T024** [P] [US1] Create `backend/tests/test_slots.py`: free_slots respects surgery/off/holiday/Sunday/past/overlap.
- [X] **T025** [US1] Create `backend/tests/test_rule_harness.py` (stretch goal): parse `data/data-pack-01/stretch/rule_tests.csv`, run each case against `validate_booking` / `validate_cancel` with `CLINIC_NOW=2026-11-02T10:00:00`, assert expected `reason_code`.

### Booking endpoints

- [X] **T026** [US1] Create `backend/app/routers/appointments.py`:
  - `POST /appointments` — patient books for self (patient_id from token), staff books with explicit patient_id (deferred to Phase 4, but keep the endpoint signature compatible). Calls `validate_booking`; on success inserts and returns the appointment.
  - `GET /appointments` — role-scoped: patient sees own, doctor sees own, staff sees all. Filters: `status`, `from_date`, `to_date`, `doctor_id`.
  - `POST /appointments/{id}/cancel` — load appointment, call `validate_cancel`, set status to `cancelled`, return. Enforce `NOT_YOUR_APPOINTMENT` (PermissionError) if patient's id doesn't match.
- [X] **T027** [US1] Create `backend/app/routers/slots.py` with `GET /slots?doctor_id=&date=&visit_type=`. Public endpoint (no auth) — used by Book page.
- [X] **T028** [US1] Mount both routers in `backend/app/main.py`.
- [X] **T029** [US1] Create `backend/tests/test_auth_scoping.py`: (a) one patient cannot read or cancel another patient's appointment, even with a direct API call — asserts 403 with `NOT_YOUR_APPOINTMENT`; (b) doctor-A's `GET /appointments` does not return any row belonging to doctor-B — asserts the response contains only doctor-A's own appointments. **This validates User Story 4 and the doctor-side of Principle III.**
- [X] **T030** [US1] Create `backend/tests/test_api_bookings.py`: end-to-end happy path (book, list, cancel, rebook same slot) using the httpx client. Every 409 response asserted in this file MUST have both `code` (non-empty, from the 17 canonical values) and `message` (non-empty) keys — assert via a shared helper `assert_refusal(resp, expected_code)`.

### Frontend — login + patient flow

- [X] **T031** [US1] Create `frontend/lib/api.ts`: typed fetch wrapper; reads token from localStorage; on 409 returns `{code, message}` for the caller to surface. Add TS types in `frontend/lib/types.ts` mirroring `schemas.py` DTOs.
- [X] **T032** [US1] Create `frontend/lib/session.ts`: `login()`, `logout()`, `getSession()` helpers. Stores token + role + id in localStorage.
- [X] **T033** [US1] Build `frontend/app/page.tsx` — role picker (Patient / Staff / Doctor) and the login form branches.
- [X] **T034** [US1] Build `frontend/app/patient/page.tsx` — patient dashboard listing upcoming appointments, each with a Cancel button that surfaces refusal messages inline (especially `INSIDE_2_HOURS`).
- [X] **T035** [US1] Build `frontend/app/patient/book/page.tsx` — doctor + specialty + date + visit_type picker, calls `GET /slots` live (SWR), submits `POST /appointments`. On 409, display the human-readable message near the offending field.

**Checkpoint (MVP):** A patient can log in, book, see, and cancel their own appointments
from the browser. All 17 reason codes are enforced. Cross-patient access is refused. The
13-row §09 verification table passes.

---

## Phase 4: User Story 2 — Staff manages every appointment (Priority: P2)

**Goal:** Staff can see every appointment, book walk-ins for any patient, and cancel
any appointment at any time (including inside the 2-hour window).

**Independent Test:** Sign in as Staff, book a walk-in for an existing patient at the
counter, then cancel an appointment that starts in one hour. Both succeed.

### Backend

- [X] **T036** [US2] In `POST /appointments` (`routers/appointments.py`), activate the staff branch: if `actor.role == "staff"`, use `body.patient_id`; set `created_by_role="staff"`. Validate `patient_id` exists.
- [X] **T037** [US2] In `validate_cancel`, the staff branch already short-circuits the 2-hour check — add a backend test confirming staff can cancel inside 2 hours (`backend/tests/test_api_bookings.py::test_staff_cancels_inside_2h`).
- [X] **T038** [US2] Create `backend/app/routers/staff.py` with `GET /staff/appointments` (role=staff only) that returns all appointments with optional `doctor_id`/`date` filters. Mount in `main.py`.

### Frontend

- [X] **T039** [P] [US2] Build `frontend/app/staff/page.tsx` — table of all appointments. Filters: doctor dropdown, date picker, status. Each row has a Cancel button that works regardless of the 2-hour gap.
- [X] **T040** [US2] Build `frontend/app/staff/book/page.tsx` — same shape as patient Book page but with an extra Patient picker (searchable by mobile).

**Checkpoint:** Staff can perform all US-2 acceptance scenarios from the browser. Phase 3
still passes.

---

## Phase 5: User Story 3 — Doctor marks visits completed (Priority: P3)

**Goal:** A doctor can see their day, open each patient's slot, and mark visits
completed. Completing a visit unlocks follow-up booking (already enforced in Phase 3's
rules engine).

**Independent Test:** Book Asha with Dr. Rao for a past slot (dev-only), sign in as Dr.
Rao, open the schedule, click **Mark completed**. Sign in as Asha, book a Cataract
follow-up — it succeeds with Dr. Rao and is refused with `FOLLOW_UP_DIFFERENT_DOCTOR` for
any other doctor.

### Backend

- [X] **T041** [US3] Add `POST /appointments/{id}/complete` to `routers/appointments.py`: load appointment; refuse with `NOT_ACTIVE` if not `booked`; require `actor.role=="doctor"` and `actor.id==appointment.doctor_id` (else 403). Call `validate_complete` (returns None). Set status, save, return.
- [X] **T042** [US3] Add `backend/tests/test_api_bookings.py::test_follow_up_requires_completed_visit`: assert a follow-up with the right doctor after completion succeeds, and with a different doctor is refused with `FOLLOW_UP_DIFFERENT_DOCTOR`.

### Frontend

- [X] **T043** [P] [US3] Build `frontend/app/doctor/page.tsx` — date picker and the day's schedule for the logged-in doctor. Each slot shows the patient name and start time.
- [X] **T044** [US3] Add the "Mark completed" button per slot in the doctor view; on success refetch the day's list. On 409 (`NOT_ACTIVE`) show the message inline.

**Checkpoint:** All three user stories work end-to-end. Every §09 row still passes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose:** Documentation, CI hygiene, and the top-level `README.md` that the brief and
LinkedIn post describe as the project's AI system design doc.

- [X] **T045** [—] Write the top-level `README.md` per the plan's §README section: 6-iteration map, ASCII architecture diagram, safety model, data-flow walkthrough, future-iteration hooks, running instructions, success metrics. Iter-1 marked ✅; Iter 2–6 marked planned.
- [X] **T046** [P] [—] Add `backend/README.md` and `frontend/README.md` with service-specific run instructions and the dependency list (for teammates not using Docker).
- [ ] **T047** [P] [—] Install pre-commit hooks locally (`pre-commit install`) so the constitution + spec guards from `.pre-commit-config.yaml` actually fire. Document the step in `README.md` §Running it.
- [ ] **T048** [—] Walk every row of `quickstart.md` end-to-end from a clean `docker compose up`. Record a 3-minute demo video (brief §10): one booking, one refusal (any of the 17), one staff cancellation.
- [ ] **T049** [—] Open a PR from `iteration-1` to `main`. Fill `.github/pull_request_template.md` linking this spec. Tag `v1.0` on `main` after merge.

**Checkpoint (iteration complete):** `main` holds the booking foundation at tag `v1.0`.
`iteration-2` can branch off from here.

---

## Dependencies & completion order

```
Phase 1 (Setup)
     ↓
Phase 2 (Foundational)
     ↓
Phase 3 (US-1 Patient Books) ◀── MVP
     ↓                 ↘
Phase 4 (US-2 Staff)   Phase 5 (US-3 Doctor)   ← can run in parallel after Phase 3
     ↘                 ↙
Phase 6 (Polish, docs, demo, PR, tag v1.0)
```

- **Phase 2 blocks everything else.** The pure rule/slot skeletons exist so Phase 3 can
  import them, but the rule logic itself lands in Phase 3 (it's the MVP's heart).
- **Phase 3 (MVP) is sufficient for a thin demo.** Even without Phase 4 or 5, a patient
  can log in, book, see, and cancel.
- **Phases 4 and 5 are independent** — they can proceed in parallel once Phase 3 is
  complete.
- **Phase 6 waits for Phases 3–5** so the demo video covers all three roles.

## Parallel execution examples

Within Phase 3 (all marked `[P]`):
- T022 (conftest), T023 (test_rules.py), T024 (test_slots.py) can be written by three
  agents simultaneously — different files, no shared state.

Within Phase 4:
- T039 (staff frontend) is `[P]` against any Phase-5 frontend tasks that start
  simultaneously.

## Implementation strategy (MVP first, incremental delivery)

1. **Ship the MVP first.** Phases 1 → 2 → 3 land the patient flow and rule engine. At this
   point you can record a demo for a thin slice.
2. **Add Staff next** (Phase 4). This unlocks the "Inside 2 hours → contact Staff" story.
3. **Add Doctor last** (Phase 5). Follow-ups need a completed visit; without Phase 5
   you'd have to seed completions manually.
4. **Polish and PR** (Phase 6). Record the demo, write the AI-architecture README, open
   the PR, merge, tag `v1.0`.

## Verification matrix

| spec.md scenario | task | Verifies |
|---|---|---|
| US-1 #1 (happy path) | T026 + T030 + T035 | A booking succeeds |
| US-1 #2–11 (10 refusals) | T019 + T023 + T026 | Every reason code fires |
| US-1 #12 `INSIDE_2_HOURS` | T020 + T030 | Patient cancel inside 2h |
| US-1 #13 (rebook cancelled) | T021 + T030 | Slot reopens after cancel |
| US-2 scenarios | T036–T040 | Staff manages everything |
| US-3 scenarios | T041–T044 | Doctor completes; follow-up unlocked |
| US-4 scenarios | T013 + T029 | Cross-patient AND cross-doctor access refused; refusal shape (`code` + `message`) asserted |

## Notes

- **File-level `[P]` discipline:** two tasks tagged `[P]` must touch disjoint files. If a
  later task reorders imports in a file touched by `[P]`, drop the `[P]` tag.
- **Protected files:** T019 (`rules.py`) and T021 (`slots.py`) trigger CODEOWNERS.
  Review deliberately. Any later iteration that wants to change these files does so
  through a new spec, not a direct edit.
- **No new reason codes.** The 17 codes in `docs/conventions.md` §2 are the public
  contract. If a new refusal case appears, discuss with the reviewer — adding a code is a
  constitution amendment.
