# frontend/ — NetraCare web client

Next.js 14 (App Router) + TypeScript + Tailwind CSS. One SPA with three
role-scoped sections.

## Quick start (inside Docker — recommended)

```bash
# from repo root
docker compose up frontend
```

Open <http://localhost:3000>.

## Local dev (without Docker)

```bash
cd frontend
corepack enable
pnpm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev
```

## Routes

| Path | Role | What it does |
|---|---|---|
| `/` | — | Role picker + lightweight sign-in |
| `/patient` | Patient | Dashboard — upcoming appointments, cancel own |
| `/patient/book` | Patient | Pick doctor + speciality + date + visit type + slot → book |
| `/staff` | Staff | All-appointments table with filters + cancel (any time) |
| `/staff/book` | Staff | Walk-in booking: patient ID + the slot picker |
| `/doctor` | Doctor | Day picker + own schedule + **Mark completed** |

## Module map

| File | Purpose |
|---|---|
| `lib/types.ts` | TypeScript mirror of backend Pydantic DTOs |
| `lib/api.ts` | Typed fetch wrapper. Throws `ApiError` on 409/403 with `.code` and `.message` |
| `lib/session.ts` | LocalStorage bearer-token helpers |
| `app/layout.tsx` | Global shell, Tailwind base |
| `app/page.tsx` | `/` — role picker + login |
| `app/patient/*` | Patient routes |
| `app/staff/*` | Staff routes |
| `app/doctor/page.tsx` | Doctor route |

## Design discipline

- **No business rules here.** If the backend returns a 409, the UI
  displays `error.message` inline. The 17 reason codes live only in
  `backend/app/errors.py`; the frontend never maps them.
- **Session is localStorage.** No cookies, no CSRF concerns in this
  classroom-grade iteration. If a fetched call returns 401, the client
  bounces back to `/`.
- **Tailwind only.** No design system, no component library yet. Keep
  interactions functional; polish later iterations.
