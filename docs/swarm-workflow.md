# Swarm workflow

This document is the execution model for the NetraCare AI agent swarm.
Every specialist agent in `.claude/agents/` references this doc. Every
human orchestrating a feature follows it.

**Audience:** humans dispatching work AND the subagents themselves.

**Prerequisite reading for anyone (human or agent):**
1. `.specify/memory/constitution.md`
2. `docs/conventions.md`
3. This file

---

## 1. The agents

| Agent | Role | Write scope |
|---|---|---|
| **orchestrator** | Decomposes feature → task cards | none (produces text) |
| **spec** | WHAT and WHY | `specs/**/spec.md`, `checklists/` |
| **architect** | HOW | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `tasks.md`, `quickstart.md` |
| **backend** | API, business logic, LLM modules | `backend/app/**` (except `rules.py`, `slots.py`), `pyproject.toml` |
| **frontend** | Next.js UI | `frontend/**` |
| **security** | PHI, auth, secrets, deps review | none (review-only) |
| **qa** | Tests | `backend/tests/**`, `frontend/tests/**` |
| **integration** | Docker, env, cross-service wiring | `docker-compose*.yml`, Dockerfiles, `.env.example`, `scripts/` |
| **review** | Pre-PR sweep | none (review-only) |

**Protected files** (require explicit human invocation, enforced by
`CODEOWNERS` + pre-commit):
- `.specify/memory/constitution.md`
- `specs/**/spec.md`
- `backend/app/rules.py`
- `backend/app/slots.py`
- `docs/conventions.md` (this file is CODEOWNERS-protected too)

No agent other than its designated owner may write to another agent's
scope. If a task spans two scopes, split it into two task cards.

---

## 2. Execution flow (one iteration or feature)

```
  Human defines the feature
       │
       ▼
  orchestrator  ──▶  task cards appended to docs/swarm/task-log.md
       │
       ├─ TASK-####-spec           (spec agent)
       │
       ├─ TASK-####-plan           (architect agent)      depends on spec
       │
       ├─ TASK-####-<impl-N>       (backend / frontend)   depends on plan
       │                              │
       │                              ▼
       │                           tests from qa agent
       │
       ├─ TASK-####-security       (security agent)       after impl
       │
       ├─ TASK-####-integration    (integration agent)    after impl
       │
       └─ TASK-####-review         (review agent)         last, before PR
                                     │
                                     ▼
                                  Human opens PR
                                     │
                          CODEOWNERS gate on protected files
                                     │
                               Merge → iteration branch
                               (tag v{N}.0 at iteration close)
```

Design rules (every agent and every human must respect):
- **One task, one owner agent.** No shared ownership.
- **No concurrent edits on the same file** across tasks — use separate
  worktrees if parallelising.
- **Spec first, code second.** Implementation task cards MUST cite a
  specific FR / Acceptance Scenario by number.
- **Reports are mandatory.** Every agent's final message lists changed
  files, tests run, and known limitations.
- **No agent bypasses security or governance.** CODEOWNERS plus pre-commit
  are the belt + suspenders.

---

## 3. Task card format

Every unit of work gets one task card. Cards live in
`docs/swarm/task-log.md` as an append-only record.

```
### TASK-<NNNN>-<slug>
Iteration:    <NNN-slug>            (e.g., 002-first-llm-features)
Owner agent:  <name>                (one of the 9)
Depends on:   TASK-####-..., ...    (may be empty)
Spec ref:     <path and FR number>  (required for impl tasks)
Write scope:  <paths the owner may touch>
Read scope:   * (default)
Accept when:  <concrete, testable conditions>
Known risks:  <explicit list>
Handoff to:   <next agent, or `human` for PR open>
Status:       pending | in-progress | done | blocked
```

### Example

```
### TASK-0004-red-flag-check
Iteration:    002-first-llm-features
Owner agent:  backend
Depends on:   TASK-0001-spec, TASK-0002-plan
Spec ref:     specs/002-.../spec.md FR-R4
Write scope:  backend/app/llm/red_flags.py,
              backend/app/routers/appointments.py (wiring only)
Read scope:   *
Accept when:  * tests/test_red_flags.py passes for the 5 categories
              * booking is refused if the LLM call fails
              * no PHI in the prompt (reviewed by security agent)
              * response under 3 s p95
Known risks:  Anthropic rate limits; prompt tuning for ambiguous input.
Handoff to:   qa
Status:       pending
```

Rule: a task with missing fields is **not valid** — the owner agent
should refuse it and ask the orchestrator (or human) to fill it in.

---

## 4. Worktrees

Parallelisable tasks run in isolated worktrees under
`../netracare-wt/<task-slug>`. This prevents cross-contamination of
uncommitted work when two agents are active at the same time.

```bash
# Create a worktree for a task
./scripts/worktree.sh new red-flag-check

# Clean it up after merge
./scripts/worktree.sh clean red-flag-check
```

Rules:
- One worktree per task, named after the task slug.
- The feature branch inside the worktree is `feature/<slug>`, branched
  from the current iteration branch (NOT from `main` directly).
- The worktree's branch merges back via PR into the iteration branch.
- Cleaning a worktree is only valid after its PR is merged.

---

## 5. Handoff template

When an agent finishes, its final message always ends with a block the
next agent (or the human) can act on without re-reading history:

```
### Handoff

From:   <me>
To:     <next agent>
Work:   <what's done>
Status: <done | needs review | blocked>
Open:   <any follow-ups>
See:    <task card + PR link if any>
```

---

## 6. When something goes wrong

- **Agent writes outside its scope.** Revert the stray changes. Update
  the agent's prompt (and this doc) to make the scope clearer.
- **Two agents touched the same file.** The last writer wins in git, but
  the TASK log catches it in review. Future tasks: use worktrees.
- **A task card is ambiguous.** The owner refuses. Orchestrator (or
  human) revises the card. No freelancing.
- **An agent proposes a protected-file change.** STOP. Only humans can
  edit protected files via the right slash command (constitution,
  specs) or a reviewed PR (rules.py, slots.py).

---

## 7. Promotion path for the orchestrator

For now, the orchestrator role is played by a human invoking the
`orchestrator` subagent for decomposition only. The human still
dispatches each resulting task card.

Promoting the orchestrator to autonomous dispatch (the brief's "Iter 4
agent" for dev-workflow) is itself a future iteration. We will only do
that once two conditions hold:
1. The task-card template has stabilised across at least two iterations.
2. We have handoff metrics (success / rework / blocked rates) worth
   feeding to an autonomous agent.
