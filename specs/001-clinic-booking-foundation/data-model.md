# Data Model — Phase 1

The database is SQLite, accessed through SQLModel. Each entity below becomes one
`SQLModel` class in `backend/app/models.py`. Validation rules trace directly to the
spec's functional requirements.

## Entities

### Doctor

| Field | Type | Notes |
|---|---|---|
| `id` | `int` | PK, autoincrement. |
| `name` | `str` | Unique. Values from `data/data-pack-01/doctors.csv`. |
| `specialities` | `str` | Semicolon-separated (matches data pack format). Normalized to a list at read time. |

**Validation:**
- `name` is unique.
- `specialities` is non-empty.

### WeeklyScheduleEntry

| Field | Type | Notes |
|---|---|---|
| `id` | `int` | PK, autoincrement. |
| `doctor_id` | `int` | FK → Doctor. |
| `weekday` | `int` | 0 = Monday, …, 5 = Saturday. (No Sunday row — clinic closed.) |
| `session` | `str` | `"AM"` or `"PM"`. |
| `status` | `str` | `"OPD"`, `"SURGERY"`, or `"OFF"`. |

**Validation:**
- Composite uniqueness: `(doctor_id, weekday, session)`.
- `session ∈ {"AM","PM"}`.
- `status ∈ {"OPD","SURGERY","OFF"}`.

**Index:** `(doctor_id, weekday)` — used by `free_slots()`.

### Holiday

| Field | Type | Notes |
|---|---|---|
| `date` | `date` | PK. |
| `reason` | `str` | Free text, from CSV. |

### Patient

| Field | Type | Notes |
|---|---|---|
| `id` | `int` | PK, autoincrement. |
| `mobile` | `str` | Unique, indexed. Primary identifier. |
| `name` | `str` | Required. |
| `year_of_birth` | `int \| None` | Reserved for Iter 2. Nullable in Iter 1. |

**Validation:**
- `mobile` is unique.

### Appointment

| Field | Type | Notes |
|---|---|---|
| `id` | `int` | PK, autoincrement. |
| `patient_id` | `int` | FK → Patient. |
| `doctor_id` | `int` | FK → Doctor. |
| `speciality` | `str` | Must be in `Doctor.specialities`. |
| `visit_type` | `str` | `"new"` (20 min) or `"follow_up"` (10 min). |
| `start_ts` | `datetime` | Timezone-naive, clinic-local. On 10-minute mark. |
| `end_ts` | `datetime` | Computed on insert from `start_ts + duration(visit_type)`. |
| `status` | `str` | `"booked"`, `"cancelled"`, or `"completed"`. |
| `created_by_role` | `str` | `"patient"` or `"staff"`. |
| `created_at` | `datetime` | Set at insert from `now()`. |

**Validation (enforced by `validate_booking`, not by the DB):**
- `speciality` is in `Doctor.specialities` (else `SPECIALITY_MISMATCH`).
- `start_ts.minute % 10 == 0` (else `INVALID_START_TIME`).
- `start_ts` > `now` (else `IN_PAST`).
- `start_ts` ≤ `now + 30 days` (else `BEYOND_30_DAYS`).
- `start_ts.weekday() != 6` (else `CLINIC_CLOSED`).
- `start_ts.date()` is not a `Holiday` (else `HOLIDAY`).
- `start_ts.time()` is inside AM (09:00–13:00) or PM (14:00–18:00) (else `OUTSIDE_SESSION`).
- `end_ts.time()` is inside the same session (else `ENDS_AFTER_SESSION`).
- `WeeklyScheduleEntry(doctor, weekday, session).status == "OPD"` (else `DOCTOR_OFF` or `SURGERY_SESSION`).
- No other `booked` Appointment overlaps `(start_ts, end_ts)` for `doctor_id` (else `DOUBLE_BOOKED`).
- No other `booked` Appointment exists for `(patient_id, speciality)` (else `ACTIVE_BOOKING_EXISTS`).
- If `visit_type == "follow_up"`: patient has at least one `completed` Appointment with this `(doctor_id, speciality)` (else `NO_PREVIOUS_VISIT`). If a `completed` Appointment exists in this `speciality` but with a different `doctor_id`, raise `FOLLOW_UP_DIFFERENT_DOCTOR`.

**State transitions:**

```
            (create)                  (cancel)
     [—] ──────────────▶ booked ──────────────▶ cancelled
                           │
                           │ (complete)
                           ▼
                        completed
```

- `cancel` from `cancelled` or `completed` raises `NOT_ACTIVE`.
- `complete` from `cancelled` or `completed` raises `NOT_ACTIVE`.
- `complete` is permitted only when `actor.role == "doctor"` and `actor.id == doctor_id`.

**Indexes:**
- `(doctor_id, start_ts)` — overlap checks + daily schedule view.
- `(patient_id, speciality, status)` — one-active-per-speciality check.
- `(patient_id, status)` — patient's "my upcoming appointments" view.

## Derived types (non-table)

### RuleError

Not persisted. Exception class:

```python
class RuleError(Exception):
    code: str   # one of the 17 canonical reason codes
    message: str  # human-readable, shown to UI
```

Raised by `rules.py` functions. Caught by FastAPI exception handler → HTTP 409 with
`{ "code": "...", "message": "..." }`.

### Session / token (in-memory)

A process-local dict `tokens: dict[str, Actor]`, where
`Actor = (role: Literal["patient","staff","doctor"], id: int)`. Not a database table —
cleared on backend restart. Not durable by design (classroom auth per Principle III
exemption + D6).

## Seed data

Loaded by `app/loader.py` at startup if the table is empty:

| CSV | → Table | Notes |
|---|---|---|
| `doctors.csv` | `Doctor` | `specialities` kept as semicolon string. |
| `weekly_schedule.csv` | `WeeklyScheduleEntry` | One row per `(doctor, weekday, session)`. `SURGERY` renders as `SURGERY`, not `SX`. |
| `holidays.csv` | `Holiday` | |
| `patients.csv` | `Patient` | 25 synthetic patients. |

The loader is idempotent — a second run with populated tables is a no-op.
