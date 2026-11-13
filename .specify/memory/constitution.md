<!--
Sync Impact Report
Version: (none) → 1.0.0  (initial ratification)
Modified principles: n/a — new document
Added sections:
  - Core Principles (5)
  - Technology & Data Standards
  - Development Workflow & Quality Gates
  - Governance
Removed sections: none
Follow-up TODOs: none
-->

# NetraCare Constitution

NetraCare is an AI front desk for a fictional eye clinic, built as a six-iteration capstone.
Every iteration adds to the previous one and ships behind the same safety guarantees. This
document is the project's highest law: it supersedes any individual feature spec, plan, or
piece of code. All AI assistants (Claude Code, Cursor, Copilot, etc.) operating in this
repository are bound by it.

## Core Principles

### I. Safety is a Backend Invariant (NON-NEGOTIABLE)

The rules engine at `backend/app/rules.py` is the **sole authority** for whether a booking,
cancel, or reschedule is permitted. Its ordered checks and canonical `reason_code` values
(see `docs/conventions.md` §2) are the contract every caller — UI, chat, agent, MCP server —
must honor.

- Business rules MUST NOT be duplicated in the frontend, in a chatbot prompt, or in an LLM
  tool description. The frontend only displays refusals it receives from the backend.
- An LLM MAY flag an appointment reason as a red flag; it MUST NOT bypass or override the
  rules engine.
- Every booking endpoint MUST call `validate_booking(...)`. Every cancel MUST call
  `validate_cancel(...)`. No side channels.

*Rationale:* Iterations 4–6 add an LLM agent that calls the API directly, with no UI in
the loop. The agent can only be as reliable as this layer. One rules engine, one truth.

### II. The Clinic Never Gives Medical Advice (NON-NEGOTIABLE)

No output surfaced to a patient — chat answer, appointment confirmation, Fact of the Day,
error message — may name a likely condition, suggest a treatment, or recommend a
medication. Red-flag symptoms always trigger the emergency response before any booking is
considered.

- Policy, procedure, and routing answers MUST cite the clinic document they came from, or
  return the fixed "I don't know" message.
- A red-flag detected by `check_red_flags` (from Iteration 2 onward) halts the booking
  flow and emits an urgent case to the Staff view, in red.
- The doctor summary (Iteration 2) may repeat diagnoses and treatments *a doctor recorded*
  and must name the recording doctor; it MUST NOT add its own diagnosis, risk, or advice.
- If the red-flag check cannot run (timeout, parse failure, API outage), the booking
  MUST be refused with "We couldn't check your reason just now."

*Rationale:* Brief §07 and the brief's success metrics make this absolute: 100% of
red-flag messages trigger the emergency response; 0 answers name a condition or suggest
treatment.

### III. Data Boundaries and Synthetic-Only Data (NON-NEGOTIABLE)

Patients access only their own data; staff access everything; doctors access their own
schedule and intake notes. Enforcement is server-side on every endpoint, via the
`current_actor()` dependency — never by the frontend.

- Direct-API tests MUST confirm that one patient cannot read or modify another patient's
  records.
- Only the data packs shipped with the course may be loaded. No real patient information
  ever enters the codebase, an LLM API call, a log file, or a commit message.
- API keys and secrets live only in `.env` (git-ignored). `.env.example` is committed with
  blank values.

*Rationale:* Brief §07 non-negotiables 4 and 5. A leaked key or a PHI exposure would end
the project.

### IV. Spec-Driven Development (NON-NEGOTIABLE)

All non-trivial work follows the spec-kit workflow:
`/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
Optional helpers (`/speckit-clarify`, `/speckit-analyze`, `/speckit-checklist`) are used
when scope is uncertain.

- No code change without a corresponding spec change. Bug fixes with no behavioral change
  may skip the spec; everything else MUST update `specs/<NNN-slug>/spec.md` first.
- The following files are protected (enforced by `CODEOWNERS` and pre-commit hooks). Edits
  require explicit human review:
  - `.specify/memory/constitution.md` (edit only via `/speckit-constitution`)
  - `specs/**/spec.md` (edit only via `/speckit-specify`)
  - `backend/app/rules.py`
  - `backend/app/slots.py`
  - `docs/conventions.md`
- Pull requests MUST answer the template question "which spec does this change correspond
  to?" Reviewers reject PRs that skip ahead to `/speckit-implement` without preceding
  artifacts.

*Rationale:* When multiple teammates use agentic coding tools, specs are the only durable
contract that prevents each tool's AI from rewriting another teammate's module.

### V. Pure Logic, Deterministic Time, Dockerized Dev Loop

Rule and slot functions accept `now` as a parameter and MUST NOT read the system clock
directly. This makes correctness testable against a fixed clock
(`CLINIC_NOW=2026-11-02T10:00:00`) that replays the 38-case stretch harness identically on
every machine.

- Rule and slot modules MUST have no FastAPI imports and no session-level side effects;
  they take data and `now` and return a decision.
- `docker compose up` is the canonical dev command. Teammates are never asked to run
  `uvicorn` or `pnpm dev` directly on their host.
- Backend and frontend each have their own Dockerfile and `.dockerignore`. Source is
  volume-mounted in dev for hot reload.
- Iteration-specific services (Chroma, Langfuse, MCP server) are reserved as commented
  slots in `docker-compose.yml` from day one and uncommented when the iteration that
  needs them lands.

*Rationale:* Testability and portability. Pure functions let graders reproduce bugs; one
canonical dev command removes an entire class of "works on my machine" issues across the
team.

## Technology & Data Standards

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLModel on SQLite. SQLite file lives
  in the host-mounted `./data/` volume.
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS. Role-scoped routes
  under `/patient`, `/staff`, `/doctor`.
- **LLM provider:** Anthropic Claude for all generative features from Iteration 2 onward.
  Provider and model name are read from `.env` so they can be swapped without a code
  change.
- **Reason codes:** The 17 canonical `reason_code` values listed in `docs/conventions.md`
  §2 are the public API contract for refusals. They MUST NOT be renamed, merged, or
  extended without a constitution amendment.
- **Visit semantics:** `visit_type ∈ {new, follow_up}`; schedule `status ∈ {OPD, SURGERY,
  OFF}`; appointment `status ∈ {booked, cancelled, completed}`. Sessions are AM
  09:00–13:00 and PM 14:00–18:00. Clinic closed Sundays and dates in `holidays.csv`.
- **Secrets:** Only in `.env` (git-ignored). `.env.example` tracks the key names.

## Development Workflow & Quality Gates

- **Branches:** `main` is always demo-ready and holds the latest merged iteration.
  `iteration-N` is the long-lived branch for each capstone iteration. Feature branches
  (`feature/<slug>`) branch off the current iteration and merge back via PR.
- **Tags:** `v1.0`, `v2.0`, ... on `main` after each iteration merge, so any iteration's
  final state can be checked out at any time.
- **Pull requests:** Use the template in `.github/pull_request_template.md`. Every PR
  must link its originating spec and confirm that the Iter-1 §09 verification table (and
  later each iteration's equivalent) still passes.
- **Verification:** For every iteration, the handout's "Done when" table is the
  acceptance test. CI (when added) runs the stretch-goal `rule_tests.csv` fixture
  against the fixed clock.
- **AI governance:** Every AI tool's rule file (`CLAUDE.md`, `AGENTS.md`,
  `.cursor/rules/`) MUST be a thin shim pointing to `docs/conventions.md`. Tool-specific
  rule drift is forbidden.

## Governance

This constitution supersedes all other project practices, spec documents, plans, and
code. Where any artifact conflicts with it, this document wins and the conflicting
artifact MUST be corrected.

**Amendment procedure.** Changes land through `/speckit-constitution` only. The command
produces a Sync Impact Report, bumps the version, and updates the `Last Amended` date.
Direct edits to this file are blocked by a pre-commit hook; bypassing the hook requires
an explicit note in the PR description.

**Versioning policy.**
- **MAJOR:** removing or redefining a non-negotiable principle, or removing a protected
  file from scope.
- **MINOR:** adding a new principle or section, or materially expanding guidance in an
  existing one.
- **PATCH:** clarifications, wording changes, typo fixes.

**Compliance review.** Every PR reviewer confirms that the change is consistent with the
five core principles. Any complexity beyond what the spec requires MUST be justified in
the PR description or rolled back. Runtime guidance for day-to-day development lives in
`docs/conventions.md`.

**Version**: 1.0.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-13
