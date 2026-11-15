# Data Model — Iteration 2

Changes on top of Iteration 1's model (see `specs/001-.../data-model.md`). All changes are additive; no Iter-1 column is renamed or dropped.

## New entities

### `PatientProfile`

| Field | Type | Constraints |
|---|---|---|
| `patient_id` | int FK → `patient.id` | PK, 1:1 with patient |
| `year_of_birth` | int | 1900 ≤ y ≤ current year |
| `general_health` | str | free text, up to ~500 chars |
| `allergies` | str | free text, up to ~500 chars |

Loaded from `data/data-pack-02/patient_profiles.csv` on startup. One row per patient.

### `UrgentCase`

| Field | Type | Constraints |
|---|---|---|
| `id` | int | PK, autoincrement |
| `patient_id` | int FK → `patient.id` | required |
| `appointment_id` | int FK → `appointment.id` nullable | null when the booking was refused post-flag |
| `reason_text` | str | the exact text the patient submitted, ≤300 chars |
| `category` | str | one of the 5 red-flag categories |
| `why` | str | the model's one-line justification, ≤200 chars |
| `created_at` | datetime (naive) | server time at creation |
| `seen_at` | datetime (naive) nullable | null = open; set when Staff clicks Mark seen |

Index: `(seen_at, created_at DESC)` for the "open urgent cases, newest first" query.

## Modified entities

### `Appointment` — two new columns

| Field | Type | Constraints |
|---|---|---|
| `reason` | str | required on INSERT, 1–300 chars (DB `VARCHAR(300) NOT NULL`) |
| `doctor_note` | str nullable | required when `status` transitions to `completed`; app-level enforcement |

Migration note: existing Iter-1 data pack rows don't carry a reason. Past visits loaded from `past_visits.csv` DO carry one — they are seeded with it. Any Iter-1 test fixtures that create appointments will be updated in the same PR.

## Data pack 2 loading

### `past_visits.csv` → `Appointment` rows

Each CSV row becomes an `Appointment` with:
- `status = "completed"`
- `reason` from CSV `reason` column
- `doctor_note` from CSV `doctor_note` column
- `start_ts` from CSV `date` + `time`
- `created_by_role = "staff"` (seeded)

These rows participate in the Iter-1 follow-up rule (FR-014 from Iter-1): a patient who has a completed visit with a doctor in a specialty can book a follow-up with that same doctor.

### `patient_profiles.csv` → `PatientProfile` rows

One row per CSV row, keyed by `patient_id`.

## Field-level role access

Who can read `Appointment.reason`:
- the booking patient ✅
- the assigned doctor ✅
- Staff ✅
- any other patient ❌ (whole appointment already hidden by Iter-1 `NOT_YOUR_APPOINTMENT`)

Who can read `Appointment.doctor_note`:
- the assigned doctor ✅
- Staff ✅
- the patient ❌ (notes are doctor-only clinical content)
- other doctors ✅ when the summary API composes across-doctor history

Who can read `PatientProfile`:
- Staff ✅
- any doctor ✅ (needed for summary across patients they open)
- the patient themselves ✅ (their own record only)
- other patients ❌

Who can read `UrgentCase`:
- Staff ✅
- the assigned doctor on the linked appointment (if any) ✅
- the patient the case is about ❌ (deliberate — they've already seen the emergency message)
- other patients ❌

## Volume estimates (classroom scale)

- `PatientProfile`: 25 rows (one per seeded patient).
- `UrgentCase`: expect ~2-5 per demo run. Index is cheap.
- `Appointment`: +27 completed rows from `past_visits.csv` at startup; ongoing rate unchanged from Iter-1.

## Backwards compatibility

- All Iter-1 endpoints that return `Appointment` gain a `reason` field in their response and (for doctor and staff views) a `doctor_note` field. No field is renamed or removed.
- Iter-1 tests that construct an `Appointment` via test helpers get a default `reason="test"` to keep them green without touching their intent.
