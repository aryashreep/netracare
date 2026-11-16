# Tasks — Iteration 2: First LLM Features

Ordered task cards per `docs/swarm-workflow.md` §3. Owner agent is declared; dependencies are explicit. Each card states a crisp "Accept when" so hand-off is unambiguous.

Execution order is top-to-bottom. Tasks within a group marked **‖ parallelizable** can be dispatched concurrently in separate worktrees.

---

## Group A — Contract & scaffolding (serial)

### TASK-0201-conventions-reason-codes
Iteration:     002-first-llm-features
Owner agent:   spec
Depends on:    —
Spec ref:      spec.md FR-004, FR-006, FR-015 · research.md D17
Write scope:   docs/conventions.md §2
Read scope:    *
Accept when:   Four new codes appended to §2 table; alphabetical order inside the "Iter 2" block; commit flagged in PR description for CODEOWNERS self-review.
Known risks:   Protected file; ensure pre-commit hook does not reject the edit.
Handoff to:    architect (done — already in this PR)

### TASK-0202-llm-deps
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0201
Spec ref:      plan.md "Primary Dependencies added"
Write scope:   backend/pyproject.toml
Read scope:    *
Accept when:   `langchain>=0.3`, `langchain-anthropic>=0.3`, `langchain-core>=0.3` added to `[project.dependencies]`; `uv lock` clean; `docker compose build backend` succeeds.
Known risks:   langchain pulls many transitive deps; keep an eye on image size.
Handoff to:    backend (llm scaffold)

### TASK-0203-env-config
Iteration:     002-first-llm-features
Owner agent:   integration
Depends on:    —
Spec ref:      research.md D11, D18 · plan.md Constraints
Write scope:   .env.example, docker-compose.yml, backend/app/config.py
Read scope:    *
Accept when:   `.env.example` gains `ANTHROPIC_API_KEY=`, `LLM_PROVIDER=anthropic`, `LLM_MODEL_FAST=claude-haiku-4-5-20251001`, `LLM_MODEL_QUALITY=claude-sonnet-4-6`, `LLM_TIMEOUT_FAST=5`, `LLM_TIMEOUT_QUALITY=8`. `docker-compose.yml` backend service passes `ANTHROPIC_API_KEY` via `env_file: .env`. `config.Settings` reads them with sane defaults.
Known risks:   Do not commit a real key.
Handoff to:    backend

---

## Group B — Data model & loader (serial)

### TASK-0204-patient-profile-model
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0201
Spec ref:      data-model.md "PatientProfile"
Write scope:   backend/app/models.py
Read scope:    *
Accept when:   `PatientProfile` SQLModel defined with FK to `Patient`; `SQLModel.metadata.create_all` creates the table on startup.
Handoff to:    backend (loader)

### TASK-0205-urgent-case-model
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0201
Spec ref:      data-model.md "UrgentCase"
Write scope:   backend/app/models.py
Read scope:    *
Accept when:   `UrgentCase` SQLModel with nullable FK to Appointment + composite index on `(seen_at, created_at)`.
Handoff to:    backend (urgent endpoints)

### TASK-0206-appointment-new-columns
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0201
Spec ref:      data-model.md "Appointment — two new columns"
Write scope:   backend/app/models.py
Read scope:    *
Accept when:   `Appointment.reason` (required 1-300 chars) + `Appointment.doctor_note` (nullable) present; existing tests updated to pass a default `reason="test"` via the factory helper.
Known risks:   Existing Iter-1 tests MUST still pass unchanged after the factory default is added.
Handoff to:    qa, backend (loader)

### TASK-0207-data-pack-02-loader
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0204, TASK-0205, TASK-0206
Spec ref:      data-model.md "Data pack 2 loading" · FR-001, FR-002
Write scope:   backend/app/loader.py
Read scope:    data/data-pack-02/
Accept when:   On startup (and on seed call), loader reads `patient_profiles.csv` into `PatientProfile` rows and `past_visits.csv` into completed `Appointment` rows. Idempotent. Log line: `Seed loaded: ... 25 profiles, +27 past visits`. Asha Verma (P01) has 3 completed visits after seeding.
Known risks:   CSV date/time parsing; use existing Iter-1 helpers.
Handoff to:    qa

---

## Group C — LLM module (‖ parallelizable among chains after scaffold)

### TASK-0208-llm-scaffold
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0202, TASK-0203
Spec ref:      plan.md "LLM module" · FR-008
Write scope:   backend/app/llm/__init__.py, backend/app/llm/client.py, backend/app/llm/prompts/
Read scope:    *
Accept when:   `backend/app/llm/client.py` exposes `get_fast_model()` and `get_quality_model()` via `init_chat_model(...)` with provider + model + timeout from settings. Prompts directory exists; empty file stubs for each chain's prompt.
Handoff to:    backend (per-chain tasks below)

### TASK-0209-check-red-flags-chain ‖
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0208
Spec ref:      FR-011, FR-012 · research.md D13, D14, D15 · spec.md US-1
Write scope:   backend/app/llm/red_flag.py, backend/app/llm/prompts/red_flag.md
Read scope:    *
Accept when:   `check_red_flags(reason: str) -> RedFlagResult` returns Pydantic `{red_flag, category, why}`. Prompt split: stable prefix (categories + examples + format) + volatile suffix (`{reason}`). Cache-control marker on prefix. Timeout from settings. Raises `RedFlagCheckError` on any failure (timeout, HTTP, parse). Token budget guard: >2,000 input tokens → raises.
Known risks:   Pydantic schema must align with FR-011 exactly.
Handoff to:    qa, security

### TASK-0210-fact-of-the-day-chain ‖
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0208
Spec ref:      FR-016 to FR-019 · research.md D15 · spec.md US-2
Write scope:   backend/app/llm/fact.py, backend/app/llm/prompts/fact.md
Read scope:    *
Accept when:   `generate_fact(previous: str | None) -> str` returns ≤2 sentences, no condition/treatment/medicine/product names. On any failure, raises `FactUnavailable` (endpoint catches and returns fallback).
Handoff to:    qa, frontend

### TASK-0211-doctor-summary-chain ‖
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0208
Spec ref:      FR-020 to FR-024 · research.md D13 · spec.md US-3
Write scope:   backend/app/llm/summary.py, backend/app/llm/prompts/summary.md
Read scope:    *
Accept when:   `summarize_patient(profile, today_reason, past_visits) -> str` returns ≤120 words, restates only inputs, names doctor per item. Uses quality model. Token budget guard ≤4,000. Raises `SummaryUnavailable` on failure.
Handoff to:    qa, security

### TASK-0212-prompt-cache-headers
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0209, TASK-0210, TASK-0211
Spec ref:      research.md D13, D18 · SC-007
Write scope:   backend/app/llm/client.py, backend/app/llm/*.py
Read scope:    *
Accept when:   Anthropic `cache_control: {"type": "ephemeral"}` applied at the end of each stable prefix. Logged structured line per call: `chain, model, input_tokens, output_tokens, cache_read_tokens, latency_ms, cache_hit`.
Handoff to:    qa

---

## Group D — API endpoints (serial after chains)

### TASK-0213-constants-emergency-message
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0201
Spec ref:      spec.md "Emergency text is literal" · FR-013
Write scope:   backend/app/constants.py (new)
Read scope:    *
Accept when:   `EMERGENCY_MESSAGE` constant holds the handout §04-R4 string verbatim. Imported wherever red-flag responses are assembled.
Handoff to:    backend

### TASK-0214-appointments-reason-field
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0206, TASK-0213
Spec ref:      FR-004, FR-005 · contracts/api.md "Modified POST /appointments"
Write scope:   backend/app/routers/appointments.py, backend/app/schemas.py
Read scope:    *
Accept when:   Request schema requires non-empty `reason` ≤300 chars; missing → 400 `REASON_REQUIRED`; too long → 400 `REASON_TOO_LONG`. Field surfaced on reads per role scoping (patient sees own, doctor sees assigned, staff sees all).
Handoff to:    qa

### TASK-0215-red-flag-pre-check-wiring
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0209, TASK-0205, TASK-0213, TASK-0214
Spec ref:      FR-013, FR-014, FR-015 · spec.md US-1
Write scope:   backend/app/routers/appointments.py
Read scope:    *
Accept when:   `POST /appointments` calls `check_red_flags(reason)` BEFORE `validate_booking`. On `red_flag=true`: create `UrgentCase` (persisted regardless of subsequent outcome), include `red_flag` in response, continue to rules check. On `RedFlagCheckError`: return 503 `RED_FLAG_CHECK_UNAVAILABLE`, no appointment, no urgent case. Must NOT touch rules.py/slots.py.
Known risks:   Protected-file adjacency. Verify no edits leaked into rules.py.
Handoff to:    qa, security

### TASK-0216-appointments-complete-required-note
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0206
Spec ref:      FR-006, FR-007 · contracts/api.md "Modified POST /appointments/{id}/complete"
Write scope:   backend/app/routers/appointments.py, backend/app/schemas.py
Read scope:    *
Accept when:   `POST /appointments/{id}/complete` requires non-empty `doctor_note`; missing → 400 `NOTE_REQUIRED`. Note persisted and surfaced to doctor + staff reads.
Handoff to:    qa

### TASK-0217-urgent-cases-endpoints
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0205, TASK-0215
Spec ref:      FR-025, FR-026, FR-027 · contracts/api.md "New: GET /urgent-cases"
Write scope:   backend/app/routers/urgent.py (new), backend/app/main.py
Read scope:    *
Accept when:   `GET /urgent-cases` (staff-only) returns open cases newest-first. `POST /urgent-cases/{id}/seen` is idempotent. Appointment list endpoints gain `urgent: bool` when a linked UrgentCase exists.
Handoff to:    qa, frontend

### TASK-0218-fact-of-the-day-endpoint
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0210
Spec ref:      FR-016 to FR-019 · contracts/api.md "New: GET /fact-of-the-day"
Write scope:   backend/app/routers/facts.py (new), backend/app/main.py
Read scope:    *
Accept when:   `GET /fact-of-the-day?previous=...` returns `{fact, caveat}`; caveat is constant text; on `FactUnavailable` returns fixed fallback + caveat with HTTP 200.
Handoff to:    qa, frontend

### TASK-0219-doctor-summary-endpoint
Iteration:     002-first-llm-features
Owner agent:   backend
Depends on:    TASK-0211, TASK-0204
Spec ref:      FR-020 to FR-024 · contracts/api.md "New: GET /doctor/patients/{patient_id}/summary"
Write scope:   backend/app/routers/doctor.py
Read scope:    *
Accept when:   Doctor-only (403 otherwise with `NOT_YOUR_APPOINTMENT`). Assembles profile + today's reason + past visits. Returns `{summary, past_visits, profile}`; on `SummaryUnavailable`, `summary` is the fallback string and raw data still present.
Known risks:   Role check must match Iter-1 pattern exactly.
Handoff to:    qa, security

---

## Group E — Frontend (‖ parallelizable among features)

### TASK-0220-booking-form-reason-input ‖
Iteration:     002-first-llm-features
Owner agent:   frontend
Depends on:    TASK-0214
Spec ref:      FR-004 · contracts/api.md
Write scope:   frontend/app/patient/book/**, frontend/app/staff/book/**, frontend/lib/api.ts
Read scope:    *
Accept when:   Both patient and staff booking forms have a required `reason` textarea (max 300 chars, counter visible). Error states render the server's `code`/`message`. On red-flag response, emergency message is displayed prominently in red above any other outcome.
Handoff to:    qa

### TASK-0221-patient-fact-of-the-day-card ‖
Iteration:     002-first-llm-features
Owner agent:   frontend
Depends on:    TASK-0218
Spec ref:      FR-016, FR-017 · spec.md US-2
Write scope:   frontend/app/patient/page.tsx, frontend/app/patient/components/FactCard.tsx
Read scope:    *
Accept when:   Fact card renders on patient home with caveat beneath; Refresh button calls endpoint with `previous=<current>`; loading and fallback states handled.
Handoff to:    qa

### TASK-0222-staff-urgent-view ‖
Iteration:     002-first-llm-features
Owner agent:   frontend
Depends on:    TASK-0217
Spec ref:      FR-025, FR-026 · spec.md US-6
Write scope:   frontend/app/staff/page.tsx, frontend/app/staff/components/UrgentList.tsx
Read scope:    *
Accept when:   Urgent list at top of staff view with patient, reason, category, why, timestamp; Mark seen removes from open list and refreshes.
Handoff to:    qa

### TASK-0223-urgent-tag-on-appointments ‖
Iteration:     002-first-llm-features
Owner agent:   frontend
Depends on:    TASK-0217
Spec ref:      FR-027
Write scope:   frontend/app/staff/**, frontend/app/doctor/**
Read scope:    *
Accept when:   Any appointment row where `urgent === true` shows a red "Urgent" badge in staff and doctor schedule views.
Handoff to:    qa

### TASK-0224-doctor-complete-note-input ‖
Iteration:     002-first-llm-features
Owner agent:   frontend
Depends on:    TASK-0216
Spec ref:      FR-006 · spec.md US-5
Write scope:   frontend/app/doctor/schedule/**, frontend/app/doctor/components/CompleteDialog.tsx
Read scope:    *
Accept when:   Mark completed opens a dialog requiring a non-empty note; disabled submit until note typed; server error (`NOTE_REQUIRED`) surfaced inline.
Handoff to:    qa

### TASK-0225-doctor-patient-summary-view ‖
Iteration:     002-first-llm-features
Owner agent:   frontend
Depends on:    TASK-0219
Spec ref:      FR-020, FR-023, FR-024 · spec.md US-3
Write scope:   frontend/app/doctor/patient/[id]/page.tsx
Read scope:    *
Accept when:   Page shows "AI summary of recorded notes. Check the notes below." label + summary text + full past notes list beneath + profile sidebar. Fallback label rendered when `summary` is the fallback string.
Handoff to:    qa

---

## Group F — Tests, security, integration (parallel after features land)

### TASK-0226-backend-unit-tests-parsers-and-budget
Iteration:     002-first-llm-features
Owner agent:   qa
Depends on:    TASK-0209, TASK-0210, TASK-0211, TASK-0212
Spec ref:      SC-006
Write scope:   backend/tests/test_llm_unit.py (new)
Read scope:    *
Accept when:   Tests for: Pydantic parser on red-flag (happy + malformed → raises); prompt-assembly functions (PHI-free prefix); token-budget guard raises on overrun; emergency message constant matches handout text byte-for-byte.
Handoff to:    review

### TASK-0227-backend-tests-endpoint-contracts
Iteration:     002-first-llm-features
Owner agent:   qa
Depends on:    TASK-0215, TASK-0216, TASK-0217, TASK-0218, TASK-0219
Spec ref:      FR-004 to FR-027 · SC-005, SC-008
Write scope:   backend/tests/test_api_iter2.py (new), backend/tests/conftest.py
Read scope:    *
Accept when:   Tests cover: `REASON_REQUIRED`, `REASON_TOO_LONG`, `NOTE_REQUIRED`, red-flag mocked positive and negative paths, `RED_FLAG_CHECK_UNAVAILABLE` on mocked chain failure, urgent case persisted even when rules refuse, urgent list ordering, Mark seen idempotence, summary 403 for non-doctor, summary fallback on mocked chain failure, cross-patient reason not disclosed.
Known risks:   Mock the LLM client; never hit a real API from unit tests.
Handoff to:    review

### TASK-0228-red-flag-harness ‖
Iteration:     002-first-llm-features
Owner agent:   qa
Depends on:    TASK-0209
Spec ref:      Handout §11 stretch · SC-001
Write scope:   backend/tests/test_red_flag_harness.py (new)
Read scope:    data/data-pack-02/reason_samples.csv
Accept when:   Test iterates all 35 rows; skipped by default (`pytest.mark.live`); expected ≥18/20 red flags caught, ≤2/15 false positives. Runs with `pytest -m live` when `ANTHROPIC_API_KEY` is set.
Handoff to:    review

### TASK-0229-security-audit
Iteration:     002-first-llm-features
Owner agent:   security
Depends on:    all backend feature tasks
Spec ref:      Constitution II, III · research.md D13, D18
Write scope:   none (findings only — report in PR comment)
Read scope:    *
Accept when:   Audit confirms: no PHI in any `backend/app/llm/prompts/*.md`; summary endpoint has role gate; API key not in repo (`git grep -i ANTHROPIC_API_KEY` returns only placeholder lines); emergency message not templated through LLM.
Handoff to:    review

### TASK-0230-integration-smoke
Iteration:     002-first-llm-features
Owner agent:   integration
Depends on:    TASK-0203, all backend tasks
Spec ref:      SC-005
Write scope:   none (verification only)
Read scope:    *
Accept when:   `docker compose up --build` cleanly; `/docs` shows new endpoints; a red-flag booking with a dev API key produces an urgent case; removing the key causes `RED_FLAG_CHECK_UNAVAILABLE` on next booking and fallback fact on home.
Handoff to:    review

### TASK-0231-pre-pr-review
Iteration:     002-first-llm-features
Owner agent:   review
Depends on:    all above
Spec ref:      swarm-workflow.md
Write scope:   none
Read scope:    *
Accept when:   Checklist: spec → plan → tasks still consistent; rules.py and slots.py untouched (`git diff main -- backend/app/rules.py backend/app/slots.py` is empty); conventions §2 edit flagged in PR description; README updated with Iter-2 env vars; §09 handout table walked by hand.
Handoff to:    human (merge)

---

## Dispatch summary

```
A  → B  → C (parallel chains) → D (parallel after chains) → E (parallel) → F (parallel)
```

Critical path: `0201 → 0202 → 0208 → 0209 → 0215 → 0217 → 0227 → 0231`.
