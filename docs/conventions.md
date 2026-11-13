# NetraCare Conventions

Single source of truth for how we build NetraCare. All AI-tool rule files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/`) point here. If something is unclear, ask in the PR — do not improvise.

## 1. Architectural invariants

- **One rules engine.** Every booking rule lives in `backend/app/rules.py`. The function `validate_booking(req, session, *, now) -> None | raises RuleError(code, message)` is the only authority. Frontend never validates business rules; it only displays refusals.
- **Pure, time-injected logic.** Rule and slot functions take `now` as a parameter, never read the clock themselves. This lets the stretch-goal fixture (`CLINIC_NOW = 2026-11-02 10:00`) run all 38 cases deterministically.
- **Server-side role enforcement.** Every router uses the `current_actor()` dependency and filters by `actor.id` where applicable. The frontend cannot be the gatekeeper — later iterations have an LLM agent calling the API directly.
- **No LLM in Iter 1.** Reserve `.env` keys, but do not add LLM dependencies to `backend/pyproject.toml` until Iter 2.

## 2. Reason codes (canonical, from data pack README)

The `RuleError.code` field uses these exact strings. Do not rename.

| Code | Meaning |
|---|---|
| `INVALID_START_TIME` | Start time not on a 10-minute mark |
| `IN_PAST` | Before the clinic clock |
| `BEYOND_30_DAYS` | More than 30 days ahead |
| `CLINIC_CLOSED` | Sunday |
| `HOLIDAY` | Listed in holidays.csv |
| `OUTSIDE_SESSION` | Before 9 AM, during lunch 1-2 PM, or after 6 PM |
| `ENDS_AFTER_SESSION` | Would finish after 1 PM (AM) or 6 PM (PM) |
| `DOCTOR_OFF` | Doctor not at the clinic that session |
| `SURGERY_SESSION` | Doctor is operating that session |
| `SPECIALITY_MISMATCH` | Doctor does not cover that speciality |
| `DOUBLE_BOOKED` | Overlaps another booked appointment with that doctor |
| `ACTIVE_BOOKING_EXISTS` | Patient already has a booked appointment in that speciality |
| `NO_PREVIOUS_VISIT` | Follow-up asked for, but the patient has no completed visit in that speciality |
| `FOLLOW_UP_DIFFERENT_DOCTOR` | Follow-up must be with the doctor who saw the patient last |
| `INSIDE_2_HOURS` | Patient cancel/reschedule less than 2 hours before — goes to Staff |
| `NOT_YOUR_APPOINTMENT` | Patient acting on someone else's appointment |
| `NOT_ACTIVE` | Appointment is already cancelled or completed |

## 3. Data model vocabulary

- `visit_type` values: `new` (20 min) and `follow_up` (10 min). **Note the underscore:** the enum value is always `follow_up` in code, JSON, and CSV. In prose/docs we write "follow-up" (with a hyphen) — the two spellings refer to the same thing; the distinction matters only when grepping.
- `WeeklySchedule.status` values: `OPD`, `SURGERY`, `OFF` (match CSV).
- `Appointment.status`: `booked`, `cancelled`, `completed`.
- Sessions: AM = `09:00–13:00`, PM = `14:00–18:00`. Clinic closed Sundays and dates in `holidays.csv`.

## 4. Spec-kit workflow

All non-trivial changes follow:

```
/speckit-specify   → updates specs/00N-<slug>/spec.md
/speckit-plan      → updates plan.md, research.md, data-model.md, contracts/
/speckit-tasks     → generates tasks.md
/speckit-implement → executes
```

Clarification helpers (use when scope is uncertain):
- `/speckit-clarify` before `/speckit-plan`
- `/speckit-analyze` after `/speckit-tasks`
- `/speckit-checklist` after `/speckit-plan`

**Never jump to `/speckit-implement` without the preceding steps.**

## 5. Branch & PR flow

- `main` → always demo-ready; latest merged iteration.
- `iteration-N` → long-lived branch per capstone iteration.
- `feature/<slug>` → off the current iteration branch, PR'd back into it.
- Tag `vN.0` on `main` after each iteration merge.

Every PR must answer: **which spec file does this change correspond to?** (See `.github/pull_request_template.md`.)

## 6. Protected files (CODEOWNERS)

Edits to these files require explicit reviewer approval:
- `.specify/memory/constitution.md`
- `specs/**/spec.md`
- `backend/app/rules.py`
- `backend/app/slots.py`
- `docs/conventions.md` (this file)

## 7. Docker-first dev loop

- `docker compose up` is the canonical dev command. Never instruct a teammate to run `uvicorn` or `pnpm dev` directly.
- Backend and frontend each have their own Dockerfile and `.dockerignore`.
- Source code is volume-mounted for hot reload (dev); production builds use multi-stage.
- SQLite file lives in `./data/netracare.db` (host-mounted volume).

## 8. Fixed clock for tests

Set `CLINIC_NOW=2026-11-02T10:00:00` in `.env` to run the stretch-goal `rule_tests.csv` deterministically. When unset, code uses the real wall clock.

## 9. Secrets

API keys live in `.env` only. `.env.example` is committed; `.env` is git-ignored. Never paste keys into code, specs, or PR descriptions.
