# Nextable frontend

Both surfaces of [the spec](../docs/spec.md), talking to the real API.

## Running it

The frontend needs the backend up. In two terminals:

```bash
cd backend  && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

Then open http://localhost:5173/host. The staff password is whatever `STAFF_PASSWORD` says in `backend/.env`.

The dev server proxies `/api` to port 8000, so the app and the API share an origin and the session cookie is an ordinary first-party cookie. Nothing in the app knows the backend's address. To point it somewhere else, set `VITE_API_TARGET` (proxy target) or `VITE_API_BASE_URL` (absolute origin, for a deployed API).

A guest page lives at `/w/{token}`. Add a party and use **Open guest view** in the dialog, or **Guest link** on any queue row. Put it in a second window beside the console: both poll every five seconds, so **Notify** turns the guest screen brass within five.

The queue is stored in SQLite, so it survives a restart. `uv run python scripts/seed.py` in `backend/` loads an evening already in progress.

```bash
npm test       # which actions each status allows
npm run build  # typecheck, then a production build
```

## The API boundary

Every backend call goes through [src/api/client.ts](src/api/client.ts) and nowhere else — one function per route in section 8 of the spec, one `request` helper holding the fetch, the credentials, the query string, and the `{"detail": "..."}` error shape. No component calls `fetch`.

[src/api/types.ts](src/api/types.ts) is hand-written against the spec. Now that [openapi.yaml](../openapi.yaml) is generated from the running app, these can be replaced by generated types.

## Structure

```
src/
  api/        client.ts (the only backend boundary), types.ts, errors.ts
  components/ AddPartyForm, QueueRow, GuestLinkSheet, TodayPanel, SettingsPanel, Toast
  pages/      Host.tsx, Guest.tsx, Login.tsx
  hooks/      usePoll (the 5-second refresh), useTicker (live wait counters)
  lib/        transitions.ts (which actions a status allows), buckets.ts, format.ts
  styles/     tokens.css, base.css, host.css, guest.css
tests/        transition rules, run with vitest
```

Two rules the frontend keeps to, both from [AGENTS.md](../AGENTS.md):

- **It never owns a domain rule.** Wait estimates, positions, and which bucket a party falls into all arrive from the API. `lib/transitions.ts` decides which buttons to draw, but the service is what enforces the transition — an illegal one comes back as a 409 and surfaces as a message.
- **It never reimplements the estimator.** That lives in `backend/app/services/estimator.py`, with its rules under test there.
