# Implementation Plan: First LLM Features

**Branch**: `iteration-2` | **Date**: 2026-11-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-first-llm-features/spec.md`

## Summary

Add the first three LLM features on top of the Iteration 1 booking stack: a Fact of the Day for patients, a doctor summary, and — the one that matters for safety — a red-flag check that runs before every booking. Capture an appointment reason and a required doctor note so there is something for the LLM to work on. The LLM never decides a booking; the Iteration 1 rules engine stays frozen (CODEOWNERS-protected). Every chain is "basic LangChain" — `prompt | model | parser` — with timeouts, a cacheable stable prefix / volatile suffix split (conventions §10), and a fail-mode per feature: red-flag fails *closed* (booking refused), Fact and summary fail *open* (fallback text).

## Technical Context

**Language/Version:** Python 3.11+ (backend), TypeScript 5.x (frontend) — unchanged.

**Primary Dependencies added:**
- `langchain>=0.3`
- `langchain-anthropic>=0.3` (default provider)
- `langchain-core>=0.3` (prompt templates, parsers)
- Optional, env-gated: `langchain-openai`, `langchain-google-genai`, `langchain-groq` for provider swap.

**Storage:** Postgres 16 with pgvector pre-staged (unchanged from Iter 1 chore). Two new tables (`patient_profile`, `urgent_case`) and two new columns on `appointment` (`reason`, `doctor_note`).

**Testing:**
- Manual against §09 of the handout.
- Automated unit tests on the pure parts: Pydantic parsers, prompt-assembly functions, token-budget guard.
- `tests/test_red_flag_harness.py` iterates all 35 rows of `reason_samples.csv` as a stretch goal (skipped by default; requires API key).
- Existing 37 Iter-1 tests continue to pass with zero modification.

**Target Platform:** Unchanged — Docker Compose on macOS/Linux.

**Project Type:** Web app, same layout.

**Performance Goals:**
- Red-flag check end-to-end ≤3s p95 (5s timeout).
- Fact of the Day and summary ≤5s p95 (8s timeout).
- `GET /urgent-cases` ≤100ms p95 (indexed scan on `seen_at IS NULL`).

**Constraints:**
- No PHI in cacheable prompt prefix. Enforced by code review + a unit test that greps the prefix for forbidden tokens.
- Emergency message is a backend constant, never templated through the LLM.
- Provider swappable via `.env` with zero code change.

**Scale/Scope:**
- ~30 red-flag calls per day expected (every booking).
- ~5-10 summary calls per day (per-doctor per-patient).
- Fact of the Day: once per patient login + Refresh clicks.

## Constitution Check

*Gate — must pass before Phase 0.* Re-checked after Phase 1.

| Principle | Status | Evidence |
|---|---|---|
| I. Safety is a Backend Invariant | ✅ Pass | `rules.py` and `slots.py` are unchanged (CODEOWNERS-protected). Red-flag check is a pre-check that runs *before* `validate_booking`; it can only add refusals (`RED_FLAG_CHECK_UNAVAILABLE`), never approve one. |
| II. Clinic Never Gives Medical Advice | ✅ Pass | Fact-of-the-Day prompt explicitly forbids naming conditions, treatments, medicines, products. Caveat is backend-rendered, never LLM-output. Summary restates recorded notes only — no new advice. Security agent audit required before merge. |
| III. Data Boundaries | ✅ Pass | `reason` and `doctor_note` scoped by role on reads. Summary endpoint is doctor-only (`current_actor()` dependency). UrgentCase visible only to Staff. PHI stays in volatile suffix of every prompt — enforced by unit test. |
| IV. Spec-Driven Development | ✅ Pass | spec.md → plan.md → research.md → data-model.md → contracts/api.md → tasks.md before any code. Four new refusal codes added to the contract via a conventions §2 edit in the same PR (CODEOWNERS approval required). |
| V. Pure Logic, Deterministic Time, Dockerized | ✅ Pass | LLM chains are impure by nature (external API), isolated to `backend/app/llm/`. Prompt assembly is pure (testable). Timeouts and token counts are injected, not read from globals. `docker-compose.yml` gains one env block for `ANTHROPIC_API_KEY`. |

## Phase 0 — Research

See `research.md`. Decisions captured there:

- **D11.** LLM provider & model (Anthropic Haiku 4.5 / Sonnet 4.6, swappable via `.env`).
- **D12.** LangChain primitives only — no agent, no memory, no RAG this iteration.
- **D13.** Prompt-cache strategy per chain (stable prefix / volatile suffix), with measured targets.
- **D14.** Pydantic `PydanticOutputParser` for red-flag; string parser for Fact and summary.
- **D15.** Fail-mode per chain: red-flag closed, Fact/summary open.
- **D16.** Urgent-case persistence — dedicated table, not a flag on `Appointment`.
- **D17.** Four new refusal codes (`REASON_REQUIRED`, `REASON_TOO_LONG`, `NOTE_REQUIRED`, `RED_FLAG_CHECK_UNAVAILABLE`) added to conventions §2 contract.
- **D18.** Observability: log token count, latency, and cache-hit flag per LLM call. Full Langfuse wiring deferred to Iter 5.

## Phase 1 — Design Artefacts

- `data-model.md` — the two new tables, two new columns, FK choices, indexes.
- `contracts/api.md` — new endpoints and modified request/response shapes.
- `docs/conventions.md` §2 — four new reason codes appended (separate PR commit for CODEOWNERS review).

## Phase 2 — Task breakdown

See `tasks.md`.

Ownership summary (per swarm-workflow.md §3 task cards):

| Task group | Owner agent | Depends on |
|---|---|---|
| Spec & plan drafts | spec, architect | — |
| Reason-code contract edit (§2) | spec | spec signoff |
| `PatientProfile` + loader for data pack 2 | backend | contract |
| `UrgentCase` table + model | backend | contract |
| `reason` + `doctor_note` columns + migrations | backend | contract |
| `backend/app/llm/__init__.py` + settings | backend | — |
| `check_red_flags` chain + parser + prompt | backend | llm scaffold |
| `fact_of_the_day` chain | backend | llm scaffold |
| `doctor_summary` chain | backend | llm scaffold |
| Pre-check wiring in `POST /appointments` | backend | red-flag chain |
| `POST /appointments/{id}/complete` required-note | backend | note column |
| `GET /urgent-cases` + `POST .../seen` | backend | urgent table |
| `GET /fact-of-the-day` endpoint | backend | fact chain |
| `GET /doctor/patients/{id}/summary` endpoint | backend | summary chain |
| Patient booking form: reason field | frontend | contract |
| Patient home: Fact of the Day card + Refresh | frontend | fact endpoint |
| Staff urgent list + Mark seen | frontend | urgent endpoints |
| Doctor completion: note input | frontend | complete endpoint |
| Doctor patient page: summary + past notes | frontend | summary endpoint |
| Urgent tag in Staff/Doctor schedule views | frontend | urgent table |
| Backend tests: parsers, prompt assembly, token budget | qa | all chains |
| Backend tests: role gating on summary; cross-patient reason | qa | endpoints |
| Red-flag harness over `reason_samples.csv` | qa | red-flag chain |
| Docker: pass `ANTHROPIC_API_KEY` + `LLM_*` to backend | integration | — |
| Security audit: PHI in prefix, API key in repo, summary role check | security | all |
| Pre-PR sweep | review | all |

## Complexity tracking

| Addition | Justification | Alternative rejected |
|---|---|---|
| LangChain dependency | Instructor-mandated for Iter 2 | Raw HTTP calls — would re-implement prompt templating and parsing from scratch, no gain |
| New `UrgentCase` table | Audit trail must persist independent of the (possibly refused) appointment | Flag column on `Appointment` — loses the "flagged but booking refused" case |
| Two models (Haiku + Sonnet) | Summary quality matters; red-flag just needs classification | Single-model all-Haiku — cheaper but noisy summaries; user accepted this tradeoff |
| Four new refusal codes | Public contract must cover the new failure modes; silent HTTP codes are ambiguous | Reuse `INVALID_START_TIME`-style codes — would conflate booking rule failures with LLM infra failures |

## Open risks

- **R-01:** Anthropic API rate limits during demo. Mitigation: timeout + fallback for Fact/summary; the red-flag fail-closed path refuses the booking cleanly rather than hanging.
- **R-02:** Prompt drift. The red-flag prompt is critical safety text. Change control via `backend/app/llm/prompts/` with explicit review by the security agent.
- **R-03:** Token-budget enforcement gives false confidence if token counter is wrong. Mitigation: use the provider's own token counter, not `tiktoken`, when available.
- **R-04:** Provider swap breaks parser. Mitigation: `with_structured_output` is model-agnostic; harness run after every provider change.
