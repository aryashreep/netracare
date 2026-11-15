# API Contracts — Iteration 2

Additive to `specs/001-.../contracts/api.md`. New endpoints and modified request/response bodies only.

Every refusal body is unchanged in shape: `{ "code": "<REASON_CODE>", "message": "<human text>" }`.

## Modified: `POST /appointments`

Request body gains `reason`:

```json
{
  "doctor_id": 1,
  "speciality": "Cataract",
  "visit_type": "new",
  "start_ts": "2026-11-16T10:00:00",
  "reason": "Blurred vision for a week, especially at night"
}
```

Response — happy path (201):

```json
{
  "id": 42,
  "status": "booked",
  "reason": "Blurred vision for a week, especially at night",
  "urgent": false,
  "red_flag": null,
  "...": "all Iter-1 fields"
}
```

Response — happy path *with* red flag (201):

```json
{
  "id": 43,
  "status": "booked",
  "urgent": true,
  "red_flag": {
    "category": "sudden_vision_loss",
    "why": "Patient reports sudden loss of vision in left eye",
    "emergency_message": "What you describe needs urgent attention. Please come to the clinic now or go to the nearest emergency department. Our staff have been notified."
  },
  "...": "other fields"
}
```

Response — refused by rules AFTER red-flag raised (409):

```json
{
  "code": "SURGERY_SESSION",
  "message": "Dr. Rao is operating during this session.",
  "red_flag": { "category": "sudden_vision_loss", "why": "...", "emergency_message": "..." }
}
```

Note: the urgent case is still persisted; the client renders the emergency message even on refusal.

Refusal codes (new):
- `400 REASON_REQUIRED` — missing or empty `reason`
- `400 REASON_TOO_LONG` — `reason` > 300 chars
- `503 RED_FLAG_CHECK_UNAVAILABLE` — red-flag chain failed

## Modified: `POST /appointments/{id}/complete`

Request body gains `doctor_note`:

```json
{ "doctor_note": "OD VA 6/9, IOP 14; started latanoprost HS" }
```

Response — happy (200): the appointment with `status: "completed"` and the note.

Refusal codes (new):
- `400 NOTE_REQUIRED` — missing or empty `doctor_note`

## New: `GET /fact-of-the-day`

Query params:
- `previous` (optional) — the previous fact's text; prompt uses it to avoid repeating.

Response (200):
```json
{
  "fact": "Reading or using screens in dim light does not damage your eyes, though it can tire them faster.",
  "caveat": "General information, not medical advice"
}
```

Always 200. On LLM failure, `fact` is the fallback string.

## New: `GET /doctor/patients/{patient_id}/summary`

Auth: doctor only. Any other role → 403 `NOT_YOUR_APPOINTMENT`.

Response (200):
```json
{
  "summary": "AI summary text, up to 120 words...",
  "past_visits": [
    {
      "date": "2026-07-14",
      "doctor_name": "Dr. Shah",
      "speciality": "Retina",
      "doctor_note": "..."
    }
  ],
  "profile": {
    "year_of_birth": 1958,
    "general_health": "Type 2 diabetes, 10 years",
    "allergies": "None recorded"
  }
}
```

On LLM failure, `summary` = `"Summary unavailable. See the notes below."` — `past_visits` and `profile` always present.

## New: `GET /urgent-cases`

Auth: staff only.

Query params:
- `include_seen` (optional, default `false`) — if `true`, include cases with `seen_at` set.

Response (200):
```json
{
  "cases": [
    {
      "id": 7,
      "patient": { "id": 3, "name": "Lakshmi Nair" },
      "appointment_id": 51,
      "reason_text": "Seeing flashes of light and lots of floaters since yesterday",
      "category": "floaters_or_flashes",
      "why": "Sudden onset of new floaters and flashes",
      "created_at": "2026-11-16T14:22:03",
      "seen_at": null
    }
  ]
}
```

## New: `POST /urgent-cases/{id}/seen`

Auth: staff only.

Request: no body.

Response (200):
```json
{ "id": 7, "seen_at": "2026-11-16T14:35:19" }
```

Idempotent: a second call returns the same row unchanged.

## Modified response shape: appointment list endpoints

Every endpoint that returns `Appointment` rows (`GET /appointments`, `GET /staff/appointments`, `GET /doctor/appointments`) gains:
- `reason` (always, if the viewer is authorised — Iter-1 scoping applies)
- `doctor_note` (doctor + staff views only)
- `urgent: bool` (true when a linked `UrgentCase` exists)
