# CLAUDE.md

This is a thin shim. The source of truth for all project conventions is **`docs/conventions.md`**. Read that first, every session, before generating or editing code.

## Non-negotiable laws

These are defined formally in `.specify/memory/constitution.md` and enforced by `CODEOWNERS` + pre-commit hooks. The short version:

1. **The rules engine lives in the backend, in one place.** Never duplicate rules in the frontend.
2. **The LLM never decides a booking.** It may flag a reason; `validate_booking` is the only authority.
3. **Patients only see their own data.** Enforced server-side on every endpoint.
4. **Policy answers cite a clinic document** or say "I don't know".
5. **Synthetic data only.** No real patient information ever reaches the codebase or an LLM.

## Workflow (spec-kit)

All feature work follows spec-kit:

```
/speckit-specify  → updates spec
/speckit-plan     → updates plan
/speckit-tasks    → generates tasks
/speckit-implement → executes
```

**Do not skip to `/speckit-implement`.** If a change needs new behavior, update the spec first. Reviewers reject PRs that touch code without a corresponding spec change.

## Protected files

Never edit these without the matching slash command:
- `.specify/memory/constitution.md` → use `/speckit-constitution`
- `specs/**/spec.md` → use `/speckit-specify`
- `backend/app/rules.py` → requires reviewer approval (CODEOWNERS)
- `backend/app/slots.py` → requires reviewer approval (CODEOWNERS)

## Knowledge-graph discipline

Before writing non-trivial code, check `docs/conventions.md` and the current `specs/` folder for existing contracts. Do not reinvent utilities that already exist.

## Swarm

If you are invoked as a specialist subagent (one of the files in `.claude/agents/`), read your own agent file first AND `docs/swarm-workflow.md` AND `docs/conventions.md` before touching any file. Stay strictly inside the write scope declared in your agent file. If a task requires touching another agent's scope, STOP and request a handoff.

For humans or top-level Claude Code sessions: use the swarm by invoking subagents via the Agent tool (`subagent_type: orchestrator | spec | architect | backend | frontend | security | qa | integration | review`). Dispatch flow is in `docs/swarm-workflow.md` §2.
