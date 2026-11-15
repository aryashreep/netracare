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

## 10. Context engineering

An explicit named discipline, not a vibe. Every agent (human or AI) assembles its context from three ordered layers; shims point at layers, never duplicate them; handoffs compress state into structured artifacts instead of piping raw history.

### The three layers

| Layer | Volatility | Lives in | When to load |
|---|---|---|---|
| **1. Immutable** | Changes rarely (MAJOR constitution amendments) | `.specify/memory/constitution.md` | Once per session |
| **2. Stable** | Changes between iterations | `docs/conventions.md` (this file), `.claude/agents/*.md`, `docs/swarm-workflow.md` | At the start of each task |
| **3. Volatile** | Changes within an iteration | `specs/00N-<slug>/`, `docs/swarm/task-log.md`, open PRs | When a task card names them |

Shims (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/netracare.mdc`) are pointers to Layer 2. They MUST NOT duplicate Layer 2 content — drift would silently make different AI tools disagree.

### What we already do

- Layered memory + pointer-only shims (above).
- Scope-narrowed agent prompts (one file per agent, ≤ ~100 lines, write-scope declared in frontmatter).
- Task cards as handoff artifacts (template in `docs/swarm-workflow.md` §3). Compressed structured state, not conversation dumps.
- Stable public contracts (the 17 reason codes in §2; the five Core Principles) short-circuit re-derivation.
- Spec-kit's `/speckit-analyze` loads *only* the FR/SC/task fields it needs from spec/plan/tasks — progressive disclosure, not whole-file dumps.
- Fresh-slate per subagent invocation: every agent's prompt begins with "read first, every invocation" rather than assuming the parent session's state.

### Iteration 2+ additions (named moves)

When the first LLM features land, the following become mandatory and are measured in `specs/002-.../research.md`:

- **Prompt caching (Anthropic).** Every LLM chain in `backend/app/llm/` splits its prompt into a cacheable stable prefix (system prompt + constitution extracts + reason-code dictionary + few-shot examples) and a volatile suffix (the user's reason text). Target: **≥ 70% cache hit rate on red-flag calls**, **≥ 90% on doctor-summary calls** once prompts stabilize.
- **Context budget per LLM call.** The spec sets a hard token ceiling on each chain's input. Working defaults: **≤ 2,000 input tokens for red-flag**, **≤ 4,000 for doctor summary**, **≤ 3,000 for Fact of the Day**. Record the actual p50/p95 token counts per chain in `research.md`.
- **Fail-closed on budget overrun.** If prompt assembly exceeds its ceiling, the LLM call is skipped and the backend returns the standard "We couldn't check your reason just now" refusal — the same path as a timeout. Never silently truncate medical context.
- **Codebase index via `/graphify`.** Run at the start of each iteration; commit the index into the iteration's `specs/00N-.../` folder. Agents query it before writing non-trivial code, to find reusable modules instead of reinventing them.
- **No PHI in cached prefixes.** The stable prefix must contain zero patient-specific data. Patient profile, appointment reason, and notes always live in the volatile suffix — otherwise one patient's cache could taint another's inference.

### Who owns what

- **Architect agent** records the per-chain prompt/budget/caching plan in `research.md` and `plan.md` before implementation starts.
- **Backend agent** implements the split (cacheable prefix / volatile suffix) and surfaces the token counts in test output.
- **Security agent** audits that no PHI is in the cacheable prefix.
- **QA agent** adds a test per chain that asserts the input-token count stays under the ceiling.

## 11. Swarm conventions

From Iteration 2 onward, feature work is built by a **build-time agent swarm** — 9 specialist subagents coordinated by a human orchestrator. The full execution model is in `docs/swarm-workflow.md`.

**Short version:**

- Agents live in `.claude/agents/<name>.md`. Nine roles: `orchestrator`, `spec`, `architect`, `backend`, `frontend`, `security`, `qa`, `integration`, `review`.
- Every unit of work is a **task card** (template in `docs/swarm-workflow.md` §3). Cards are appended to `docs/swarm/task-log.md`.
- **One task, one owner agent.** No concurrent edits on the same file across tasks.
- Parallel tasks run in isolated git worktrees via `scripts/worktree.sh` (`new` / `clean` / `list`). Worktrees land at `../netracare-wt/<slug>`.
- Agents MUST stay inside their declared write scope. Protected files (`rules.py`, `slots.py`, `constitution.md`, `specs/**/spec.md`, this file) require explicit human invocation and are enforced by `CODEOWNERS` + pre-commit.
- Every agent's final message is a structured handoff block: files changed, tests run, limitations, next agent.
- Specs remain the contract. No `/speckit-implement` without `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` first.
