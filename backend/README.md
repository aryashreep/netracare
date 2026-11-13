# backend/ — NetraCare clinic API

FastAPI + SQLModel service. The source of truth for every booking rule.

## Quick start (inside Docker — recommended)

```bash
# from repo root
docker compose up backend
```

Swagger: <http://localhost:8000/docs>. Health: <http://localhost:8000/health>.

## Local dev (without Docker)

```bash
cd backend
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
DATABASE_URL=sqlite:///./netracare.db \
DATA_DIR=../data/data-pack-01 \
uvicorn app.main:app --reload
```

## Tests

```bash
pytest -v        # 37 passing, 1 stretch skipped
pytest tests/test_rules.py -v          # pure rule-engine tests
pytest tests/test_auth_scoping.py -v   # cross-role access denials
```

Fixed-clock harness:

```bash
CLINIC_NOW=2026-11-02T10:00:00 pytest tests/test_rule_harness.py -v
```

## Module map

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app, lifespan seed, CORS, exception handlers |
| `app/config.py` | `Settings` via `pydantic-settings` (`.env` driven) |
| `app/clock.py` | `now()` — honors `CLINIC_NOW`; **every rule reads time from here** |
| `app/db.py` | SQLModel engine + `get_session` dependency |
| `app/models.py` | Five SQLModel tables (Doctor, WeeklyScheduleEntry, Holiday, Patient, Appointment) |
| `app/schemas.py` | Pydantic request/response DTOs |
| `app/errors.py` | `RuleError`, the 17 canonical reason codes, and their messages |
| `app/loader.py` | Idempotent CSV seed from `data/data-pack-01/` |
| `app/auth.py` | Classroom-grade bearer tokens + `current_actor` dep |
| **`app/rules.py`** | ⚠ **Sole booking authority.** Pure, no FastAPI imports. CODEOWNERS-protected. |
| **`app/slots.py`** | ⚠ Pure slot computation. CODEOWNERS-protected. |
| `app/routers/*` | HTTP surface: `/login`, `/doctors`, `/slots`, `/appointments` |

## The 17 reason codes

Authoritative list: `docs/conventions.md` §2. Short summary: every rule
violation returns `HTTP 409 { "code": "...", "message": "..." }` with
`code` ∈ `errors.REASON_CODES`.

## Rule-engine invariants (constitution Principle I + V)

- `rules.py` and `slots.py` import nothing from FastAPI.
- They take `now: datetime` as an argument. They never call `datetime.now()`.
- `validate_booking` returns `end_ts` on success, raises `RuleError` on refusal.
- `validate_cancel` raises `PermissionError` for cross-patient attempts.

These three facts let Iterations 4–6 (agent, MCP) call the same rules
engine without any FastAPI machinery.
