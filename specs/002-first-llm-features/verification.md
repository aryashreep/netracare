# Iteration 2 — handout §09 verification

Walks every row of the handout's "Done when" table against the running
stack. Run after `docker compose up` with a real LLM provider set in
`.env` (either `LLM_PROVIDER=anthropic` with a key, or `LLM_PROVIDER=ollama`
with the model pulled). The rows marked `[no-LLM]` also work in the
degraded "no API key" mode.

Set up two shell variables once:

```bash
BASE=http://localhost:8000
TOKEN_ASHA=$(curl -s $BASE/login -X POST -H 'content-type: application/json' \
  -d '{"role":"patient","mobile":"9000000001","name":"Asha Verma"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
TOKEN_STAFF=$(curl -s $BASE/login -X POST -H 'content-type: application/json' \
  -d '{"role":"staff","name":"Reception"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
TOKEN_DR_IYER=$(curl -s $BASE/login -X POST -H 'content-type: application/json' \
  -d '{"role":"doctor","doctor_id":"D2"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
```

## Row 1 — Fact of the Day on login

```bash
curl -s $BASE/fact-of-the-day | python3 -m json.tool
```

Expect `{ "fact": "...", "caveat": "General information, not medical advice" }`.
The fact must not name a condition, treatment, medicine, or product.

## Row 2 — Refresh gives a different fact

```bash
FACT=$(curl -s $BASE/fact-of-the-day | python3 -c "import json,sys;print(json.load(sys.stdin)['fact'])")
curl -s "$BASE/fact-of-the-day?previous=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$FACT")" | python3 -m json.tool
```

Expect a different `fact` string; caveat unchanged.

## Row 3 — Benign reason books cleanly

```bash
curl -s $BASE/appointments -X POST \
  -H "Authorization: Bearer $TOKEN_ASHA" -H 'content-type: application/json' \
  -d '{"doctor_id":"D1","speciality":"Cataract","visit_type":"new","start_ts":"2026-12-02T10:00:00","reason":"Routine eye test and new glasses"}' \
  | python3 -m json.tool
```

Expect 201 with `"urgent": false`, `"red_flag": null`.

## Row 4 — Five red-flag reasons, one per category

For each phrase, repeat the booking call above with a **different** `start_ts`
(to avoid `DOUBLE_BOOKED` or `ACTIVE_BOOKING_EXISTS`) and the new reason.
Expect 201 with the emergency panel payload, matching category, and an
urgent case appearing in `GET /urgent-cases` for Staff.

| Reason | Expected category |
|---|---|
| I suddenly can't see from my left eye | `sudden_vision_loss` |
| It feels like a curtain is coming down over my right eye | `curtain_or_shadow` |
| Seeing flashes of light and lots of floaters since yesterday | `floaters_or_flashes` |
| Got floor cleaner in my eye while mopping | `chemical_or_injury` |
| Severe eye pain with headache and I feel sick | `severe_pain_headache_haloes` |

Then:

```bash
curl -s $BASE/urgent-cases -H "Authorization: Bearer $TOKEN_STAFF" | python3 -m json.tool
```

Expect 5 cases, newest first, with the correct categories.

## Row 5 — Negation and gradual descriptions do NOT trigger

```bash
# No sudden loss
curl -s $BASE/appointments -X POST \
  -H "Authorization: Bearer $TOKEN_ASHA" -H 'content-type: application/json' \
  -d '{"doctor_id":"D1","speciality":"General","visit_type":"new","start_ts":"2026-12-03T10:00:00","reason":"No sudden loss of vision but I want a check-up"}' \
  | python3 -m json.tool
# Gradual loss over years
curl -s $BASE/appointments -X POST \
  -H "Authorization: Bearer $TOKEN_ASHA" -H 'content-type: application/json' \
  -d '{"doctor_id":"D1","speciality":"General","visit_type":"new","start_ts":"2026-12-04T10:00:00","reason":"Gradual loss of vision over two years"}' \
  | python3 -m json.tool
```

Both expect 201 with `"urgent": false`, `"red_flag": null`.

## Row 6 — Red flag + Dr. Rao Thursday AM → emergency AND refusal

Pick a Thursday within the 30-day window.

```bash
curl -s $BASE/appointments -X POST \
  -H "Authorization: Bearer $TOKEN_ASHA" -H 'content-type: application/json' \
  -d '{"doctor_id":"D1","speciality":"Cataract","visit_type":"new","start_ts":"2026-11-19T10:00:00","reason":"I suddenly cannot see from my left eye"}'
```

Expect 409 `SURGERY_SESSION` **with** a `red_flag` payload. The urgent case
is still persisted (confirm via `GET /urgent-cases`).

## Row 7 — Staff marks an urgent case seen

```bash
CASE_ID=$(curl -s $BASE/urgent-cases -H "Authorization: Bearer $TOKEN_STAFF" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['cases'][0]['id'])")
curl -s $BASE/urgent-cases/$CASE_ID/seen -X POST -H "Authorization: Bearer $TOKEN_STAFF"
curl -s $BASE/urgent-cases -H "Authorization: Bearer $TOKEN_STAFF"
```

The case leaves the open list; `include_seen=true` still returns it.

## Row 8 — Complete without a note is refused `[no-LLM]`

```bash
# First book a near-past slot via Staff for Asha (requires staff role)
# then as Dr. Rao complete with empty note.
# (See the fuller script in tests/test_api_iter2.py for a drop-in replay.)
```

Expect 400 `NOTE_REQUIRED` on empty note; 200 with status `completed` on a
non-empty note.

## Row 9–11 — Doctor summary for P03, P15, P20

```bash
curl -s $BASE/doctor/patients/P03/summary -H "Authorization: Bearer $TOKEN_DR_IYER" | python3 -m json.tool
curl -s $BASE/doctor/patients/P15/summary -H "Authorization: Bearer $TOKEN_DR_IYER" | python3 -m json.tool
curl -s $BASE/doctor/patients/P20/summary -H "Authorization: Bearer $TOKEN_DR_IYER" | python3 -m json.tool
```

Expect:
- **P03 Lakshmi Nair** — summary mentions glaucoma on latanoprost
  (Dr. Iyer), early cataract (Dr. Rao), and the sulfa allergy. Nothing
  not in her notes.
- **P15 Sunita Rao** — summary says latanoprost started and timolol
  avoided because of asthma. No new warning or advice added.
- **P20 Aditya Bose** — summary says no previous visits on record and
  invents nothing.

## Row 12 — Patient cannot read the summary endpoint `[no-LLM]`

```bash
curl -s $BASE/doctor/patients/P03/summary -H "Authorization: Bearer $TOKEN_ASHA"
```

Expect 403 `NOT_YOUR_APPOINTMENT`.

## Row 13 — API key removed, restart `[no-LLM path]`

Remove `ANTHROPIC_API_KEY` from `.env` (or set `LLM_PROVIDER=ollama`
without pulling the model), `docker compose down && docker compose up`,
then:

```bash
curl -s $BASE/fact-of-the-day
curl -s $BASE/doctor/patients/P03/summary -H "Authorization: Bearer $TOKEN_DR_IYER"
curl -s $BASE/appointments -X POST \
  -H "Authorization: Bearer $TOKEN_ASHA" -H 'content-type: application/json' \
  -d '{"doctor_id":"D1","speciality":"Cataract","visit_type":"new","start_ts":"2026-12-10T10:00:00","reason":"Routine"}'
```

Expect:
- Fact: fallback text + caveat
- Summary: `"summary": "Summary unavailable. See the notes below."` + full past notes
- Booking: 503 `RED_FLAG_CHECK_UNAVAILABLE`, no appointment created

---

A pass on every row satisfies spec.md's SC-001, SC-004, SC-005, SC-008 and
the brief's §09.
