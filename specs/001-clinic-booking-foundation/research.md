# Research — Phase 0

The spec had **no `[NEEDS CLARIFICATION]` markers**, so Phase 0 is used to record the
tech-choice rationale and the dependency decisions that fall out of the spec + the
constitution. Each decision is documented with its rationale and the alternatives
considered, so later-iteration contributors understand what is intentional and what is
negotiable.

## D1. Web framework: FastAPI

**Decision:** FastAPI for the backend HTTP layer.

**Rationale:**
- Brief Iter-1 §07 specifies FastAPI as required.
- First-class Pydantic integration keeps request/response validation in one place.
- `/docs` (Swagger) is a fast sanity check during development, directly supporting the
  brief's "try it in `/docs` before building screens" workflow.

**Alternatives considered:** Flask (less Pydantic-native, no auto-OpenAPI), Django Ninja
(heavier), Starlette-only (would reinvent what FastAPI already gives us).

## D2. ORM: SQLModel

**Decision:** SQLModel (Tiangolo's wrapper on SQLAlchemy 2 + Pydantic).

**Rationale:**
- One class per entity doubles as a Pydantic model and a SQL table — reduces duplicated
  type definitions.
- Native ergonomics with FastAPI (same author).
- Easy to drop into SQLAlchemy 2 Core when needed (we won't need to in Iter 1).

**Alternatives considered:** Raw SQLAlchemy 2 + separate Pydantic DTOs (more boilerplate
for no gain at this scale), Tortoise ORM (less idiomatic for FastAPI), plain `sqlite3`
(too low-level — we would hand-roll schema migrations and session management).

## D3. Database: SQLite in a host-mounted volume

**Decision:** SQLite file at `/app/data/netracare.db`, host-mounted from `./data/`.

**Rationale:**
- Brief recommends it; zero setup; file-level durability across container restarts.
- The classroom scale (5 doctors × 25 patients × hundreds of appointments) is nowhere
  near SQLite's ceiling.
- Volume mount means the dev can inspect the database file directly with `sqlite3`.

**Alternatives considered:** Postgres service (more "production-like" but adds a
service, a connection-string story, and a startup dependency we do not need for this
scale), in-memory SQLite (would lose state across restarts — unacceptable during
multi-day development).

**Trigger to revisit:** Iteration 5's eval harness at scale, or Iteration 4's agent
concurrency tests. Switch to Postgres then if SQLite's single-writer lock becomes a
bottleneck.

## D4. Frontend: Next.js 14 (App Router) + TypeScript + Tailwind

**Decision:** Next.js 14 with the App Router, TypeScript, Tailwind for styling, and SWR
for client-side data fetching.

**Rationale:**
- Brief encourages ambition and lets the AI do the heavy lifting; Next.js is the strongest
  resume artefact and gives routing + SSR for free.
- App Router keeps per-role routes (`/patient`, `/staff`, `/doctor`) cleanly separated.
- Tailwind lets us ship three tolerable UIs quickly without a design system.
- SWR handles the "slots list refreshes after a booking" case without extra state code.

**Alternatives considered:** React + Vite (lighter, but less polished routing story),
Streamlit (brief explicitly says only if stuck — poor demo artefact), raw React with
Create React App (deprecated).

## D5. Pure rules + injected clock

**Decision:** `backend/app/rules.py` and `backend/app/slots.py` are pure modules — no
FastAPI imports, no `datetime.now()` reads. They accept `now: datetime` and a database
session, and raise `RuleError(code, message)` on refusal.

**Rationale:**
- Constitution Principle V. Lets the stretch harness replay `stretch/rule_tests.csv`
  deterministically.
- Makes the rules reusable by Iteration 2's red-flag pipeline and Iteration 4's agent
  without re-wiring.
- Testable with a plain pytest fixture — no HTTP stack required.

**Alternatives considered:** Rules as class methods on a service object (adds ceremony
for no value), rules as FastAPI dependencies (ties them to the HTTP stack — bad for
Iter 4's agent reuse).

## D6. Classroom auth: in-memory bearer tokens

**Decision:** `POST /login` returns an opaque token stored in a process-local dict
`{token: (role, id)}`; FastAPI dependency `current_actor()` reads
`Authorization: Bearer <token>`.

**Rationale:**
- Brief explicitly calls out that logins in Iter 1 are not real security — "enough for a
  classroom project" (Iter-1 §05 callout).
- No password handling, no JWT secret management, no session-store service.
- Role enforcement is still server-side on every request — satisfies Principle III.

**Alternatives considered:** JWT (overkill and a liability — one more thing to leak),
cookie-sessions (needs CSRF handling), signed state (no rotation story).

**Trigger to revisit:** Iteration 6 (partner access via MCP) — proper auth before any
real third party integration.

## D7. Package management

**Decision:** `uv` for Python, `pnpm` for Node.

**Rationale:**
- `uv` is fast, lockfile-based, and already used by `uvx` which we invoked to install
  spec-kit.
- `pnpm` is strict about phantom deps and plays well with Next.js.

**Alternatives considered:** pip + requirements.txt (works; slower; no lockfile), Poetry
(fine; slower than uv), npm (fine; weaker about phantom deps).

## D8. Docker-first development

**Decision:** `docker compose up` is the canonical dev command. Two services in
`docker-compose.yml` for Iter 1 (backend, frontend); commented placeholders reserved for
`chromadb` (Iter 3), `langfuse` (Iter 5), and `mcp-server` (Iter 6).

**Rationale:**
- Constitution Principle V. One command, same on every machine.
- `docker-compose.override.yml` adds hot-reload mounts in dev without polluting the
  production composition.

**Alternatives considered:** Local venv + `pnpm dev` directly on host (works, but drifts
between contributors), Devcontainers (more complex for the same benefit).

## D9. Testing shape

**Decision:**
- Backend: `pytest` + `httpx` async client for HTTP tests. One `test_rules.py`
  exercises the pure functions directly with a fixed-clock fixture. One
  `test_rule_harness.py` loads the stretch CSV and iterates all 38 cases.
- Frontend: no automated tests in Iter 1 (brief does not require them). Manual
  verification of the §09 table through the browser.

**Rationale:**
- Rules.py is the most load-bearing module in the entire project. Direct unit tests on
  pure functions give the most coverage for the least complexity.
- The stretch harness gives a single test file that proves the rule engine against
  the data pack's canonical cases.

**Alternatives considered:** Full BDD (overkill), Playwright frontend tests in Iter 1
(expensive for a classroom project this early).

## D10. Reason-code taxonomy

**Decision:** The 17 reason codes in `docs/conventions.md` §2 (sourced from the data
pack README) are the public refusal contract. They MUST appear in every refusal response
alongside a human-readable message.

**Rationale:**
- They are the grading rubric for the stretch harness.
- Iteration 4's agent will branch on the code string; renaming any of them breaks
  the contract.
- Making them stable now is cheaper than renaming later.

**Alternatives considered:** More granular codes (would diverge from the data pack and
break the harness), fewer codes (ambiguous — a UI message of "refused" is useless).

**Trigger to revisit:** Only through a `/speckit-constitution` amendment (per Principle
IV).
