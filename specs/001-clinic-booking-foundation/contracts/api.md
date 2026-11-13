# API Contract — Phase 1

Base URL (dev): `http://localhost:8000`. Content type: `application/json`. All
authenticated endpoints expect `Authorization: Bearer <token>` from `POST /login`.

**Refusal shape (for every 409 — rule violation):**

```json
{
  "code": "DOUBLE_BOOKED",
  "message": "That slot is already booked with the same doctor."
}
```

`code` is one of the 17 canonical values (`docs/conventions.md` §2). `message` is a
human-readable string for direct display.

**403 shape (role violation):**

```json
{ "code": "NOT_YOUR_APPOINTMENT", "message": "..." }
```

---

## POST /login

Issue a session token for one of the three roles.

**Body (one of):**
```json
{ "role": "patient", "mobile": "9000000001", "name": "Asha Verma" }
{ "role": "staff", "name": "Priya" }
{ "role": "doctor", "doctor_id": 1 }
```

For `patient`: if `mobile` is unknown, a new `Patient` is created with the given `name`.

**200:**
```json
{ "token": "opaque-string", "role": "patient", "id": 7 }
```

**422:** malformed body.

---

## GET /doctors

Public — no auth required (used by the login screen too).

**200:**
```json
[
  { "id": 1, "name": "Dr. Anand Rao", "specialities": ["Cataract", "General"] },
  { "id": 2, "name": "Dr. Meera Iyer", "specialities": ["Glaucoma", "Cataract"] },
  ...
]
```

---

## GET /slots

List bookable start times.

**Query:**
- `doctor_id` (int, required)
- `date` (ISO date, required, e.g. `2026-11-20`)
- `visit_type` (`new` or `follow_up`, required)

**200:**
```json
{
  "doctor_id": 1,
  "date": "2026-11-20",
  "visit_type": "new",
  "slots": ["2026-11-20T09:00:00", "2026-11-20T09:10:00", ...]
}
```

**Notes:**
- Returns an empty list (not an error) if the date is Sunday, a holiday, in the past, or
  the doctor has no OPD session that weekday.
- Slots in overlapping time with existing `booked` appointments are omitted.

---

## POST /appointments

Create a booking.

**Auth:** patient (books for self) or staff (books for anyone).

**Body:**
```json
{
  "doctor_id": 1,
  "speciality": "Cataract",
  "visit_type": "new",
  "start_ts": "2026-11-20T10:00:00",
  "patient_id": 7
}
```

- `patient_id` is required for staff, ignored for patient (server uses `actor.id`).

**201:**
```json
{
  "id": 42,
  "patient_id": 7,
  "doctor_id": 1,
  "speciality": "Cataract",
  "visit_type": "new",
  "start_ts": "2026-11-20T10:00:00",
  "end_ts": "2026-11-20T10:20:00",
  "status": "booked"
}
```

**409:** any rule violation. See refusal shape above. One of the 17 reason codes.

**403:** role violation (e.g. patient providing another `patient_id`).

---

## GET /appointments

List appointments visible to the caller.

**Auth:** any role.

**Query:** (optional) `status`, `from_date`, `to_date`, `doctor_id`, `patient_id`.

**Visibility rules (server-enforced):**
- `patient` role: only own appointments. `patient_id` query param is ignored.
- `doctor` role: only own appointments (doctor_id = actor.id).
- `staff` role: everyone.

**200:**
```json
[
  { "id": 42, "patient": { "id": 7, "name": "Asha Verma" }, "doctor": {...}, "speciality": "Cataract", "visit_type": "new", "start_ts": "...", "end_ts": "...", "status": "booked" },
  ...
]
```

---

## POST /appointments/{id}/cancel

Cancel an appointment.

**Auth:** patient (own only) or staff (anyone).

**200:**
```json
{ "id": 42, "status": "cancelled" }
```

**409:**
- `NOT_YOUR_APPOINTMENT` — patient asking about someone else's.
- `NOT_ACTIVE` — already cancelled or completed.
- `INSIDE_2_HOURS` — patient role, under 2 hours to start. (Staff can override; same
  request from staff succeeds.)

---

## POST /appointments/{id}/complete

Mark a booked appointment as completed.

**Auth:** doctor only, and only the doctor assigned to the appointment.

**200:**
```json
{ "id": 42, "status": "completed" }
```

**409:**
- `NOT_ACTIVE` — already cancelled or completed.

**403:** different doctor, or non-doctor role.

---

## GET /staff/appointments

Staff-only broader view.

**Auth:** staff.

**Query:** `doctor_id`, `date` (optional filters).

**200:** same shape as `GET /appointments` but across all patients and doctors.

---

## Reason-code reference

For completeness, every 409 response uses one of these `code` values:

`INVALID_START_TIME`, `IN_PAST`, `BEYOND_30_DAYS`, `CLINIC_CLOSED`, `HOLIDAY`,
`OUTSIDE_SESSION`, `ENDS_AFTER_SESSION`, `DOCTOR_OFF`, `SURGERY_SESSION`,
`SPECIALITY_MISMATCH`, `DOUBLE_BOOKED`, `ACTIVE_BOOKING_EXISTS`, `NO_PREVIOUS_VISIT`,
`FOLLOW_UP_DIFFERENT_DOCTOR`, `INSIDE_2_HOURS`, `NOT_YOUR_APPOINTMENT`, `NOT_ACTIVE`.

See `docs/conventions.md` §2 for authoritative definitions.
