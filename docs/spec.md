# Nextable — Restaurant Waitlist Manager

**Status:** approved specification  
**Date:** 2026-09-12  
**Project:** AI Dev Tools Zoomcamp 2026 — homework 02

---

## 1. Overview

Nextable replaces the paper list and the buzzer at a restaurant's front door. A host adds walk-in parties to a queue, the app quotes each party a wait time that improves as the restaurant serves more guests, and each party gets a private link showing their live position. When a table opens, the host taps **Notify** and the guest's page turns into a full-screen "table ready" card.

The name is "next" + "table" — the next available table.

## 2. Goals

- A host can run an entire service from one screen without touching paper.
- A guest can see their position and expected wait without asking the host.
- Wait quotes start from sane defaults and get more accurate as real turnaround data accumulates.
- The app is fully demonstrable offline: no third-party accounts, no API keys, no per-message costs.

## 3. Non-goals

Explicitly out of scope. These are deliberate omissions, not oversights:

- Real SMS or push notifications (no Twilio, no account required).
- Table inventory and table assignment. Capacity is a configured number per party-size bucket, not a set of table records.
- Reservations and bookings. Walk-ins only.
- Multiple restaurants / multi-tenancy.
- User accounts, registration, and roles. One shared staff password.
- POS, kitchen, or payment integration.
- Analytics beyond a single-day operational summary.
- Internationalization.

## 4. Users and surfaces

| Surface | Route | Who | Auth |
|---|---|---|---|
| Host console | `/host` | Front-of-house staff, on a tablet or laptop at the door | Shared staff password |
| Guest status page | `/w/{token}` | A waiting party, on their own phone | None — the token is the credential |

## 5. Domain model

### 5.1 `Party`

The single core entity.

| Field | Type | Notes |
|---|---|---|
| `id` | int, PK | |
| `token` | str, unique, indexed | URL-safe random, >= 128 bits of entropy (`secrets.token_urlsafe(16)`) |
| `name` | str | Party name as given at the door |
| `size` | int | Number of people, >= 1 |
| `phone` | str, nullable | Recorded for the host's own reference only; never used to send anything |
| `note` | str, nullable | e.g. "highchair", "patio preferred" |
| `status` | enum | See 5.2 |
| `quoted_wait_minutes` | int | The quote given at join time. Frozen — never updated. Used to score accuracy. |
| `joined_at` | datetime, UTC | |
| `notified_at` | datetime, UTC, nullable | |
| `seated_at` | datetime, UTC, nullable | |
| `closed_at` | datetime, UTC, nullable | Set when the party reaches any terminal status |

A party is **active** when its status is `WAITING` or `NOTIFIED`. Active parties are the queue.

Turnaround for a seated party is `seated_at - joined_at`. This is the quantity the estimator learns from.

### 5.2 Status lifecycle

```
WAITING ──notify──> NOTIFIED ──seat──> SEATED      (terminal)
   │                    │
   │                    ├──no-show──>  NO_SHOW     (terminal)
   │                    └──cancel──>   CANCELLED   (terminal)
   ├──seat────────────────────────────> SEATED     (terminal, seated straight from the queue)
   └──cancel──────────────────────────> CANCELLED  (terminal)
```

Rules:

- `NO_SHOW` is reachable only from `NOTIFIED`. A party that was never called cannot be a no-show; cancel it instead.
- Terminal statuses are final. Any transition out of one is rejected.
- Transitions are enforced in the service layer, not in the router and not in the frontend. An illegal transition returns **409 Conflict** with a message naming the current and attempted status. It must never be a silent no-op.

### 5.3 `Config`

A single row holding operational settings (see section 7). Editable from the host console so the demo can be tuned live.

## 6. Wait estimation

This is the only real domain logic in the app, and it is deliberately the most carefully specified part of this document.

### 6.1 Size buckets

Party sizes map to four buckets. A bucket is the unit of both capacity and learning, because a two-top and an eight-top turn over at very different rates.

| Bucket | Sizes | Default turn (min) | Default table count |
|---|---|---|---|
| `SMALL` | 1–2 | 25 | 8 |
| `MEDIUM` | 3–4 | 40 | 6 |
| `LARGE` | 5–6 | 55 | 3 |
| `XLARGE` | 7+ | 75 | 1 |

`table_count` is a capacity divisor — how many parties of that bucket the venue can serve in parallel. It is a configured number, not a set of table records.

### 6.2 Effective turn time

For each bucket, keep the turnaround times of the last `N = 20` parties that reached `SEATED`. Let `n` be how many samples exist (0 to N) and `observed_avg` their mean. Blend toward the configured prior with a smoothing constant `m = 5`:

```
effective_turn(bucket) = (n * observed_avg + m * default_turn) / (n + m)
```

With no history the quote is exactly the configured default. As real data arrives the prior fades. This shrinkage is what makes the app sane on its first night and accurate on its tenth.

### 6.3 The quote

```
parties_ahead = count of ACTIVE parties in the same bucket
                that joined strictly earlier than this party

quote_minutes = ceil(parties_ahead / table_count) * effective_turn(bucket)
```

Rounded up to the nearest 5 minutes for display. A quote of 0 means no one is ahead in that bucket and the party is shown as "we can seat you now".

### 6.4 Live recalculation

`quoted_wait_minutes` is frozen at join time. The **current** estimate shown to a waiting party is recomputed on every read using the queue as it stands now, so positions and times fall as parties ahead get seated. The frozen quote is retained only to score accuracy in the stats view.

### 6.5 Testability

`services/estimator.py` is a pure module: it takes a bucket, a list of turnaround samples, a count of parties ahead, and the config, and returns an integer. It performs no database access and no clock reads. Every rule above is a unit test with hand-seeded data.

## 7. Configuration

Exposed at `GET|PUT /api/config`, editable from the host console:

- Per bucket: `default_turn_minutes`, `table_count`.
- `history_window` (`N`, default 20).
- `smoothing_constant` (`m`, default 5).
- `restaurant_name` — shown on the guest page.

Environment variables (not in the database): `STAFF_PASSWORD`, `SESSION_SECRET`, `DATABASE_URL`.

## 8. API contract

Documented in `openapi.yaml` at the repository root and hand-written first, so the frontend can be built against it before the backend exists. Once the backend is real, FastAPI's generated schema becomes the source of truth and the hand-written file is replaced by an export of it.

All timestamps are ISO-8601 UTC. All request and response bodies are JSON.

### 8.1 Auth

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/auth/login` | `{password}` | 204 + `HttpOnly` session cookie; 401 on failure |
| POST | `/api/auth/logout` | — | 204, clears the cookie |
| GET | `/api/auth/me` | — | 200 if the session is valid, 401 otherwise |

### 8.2 Host — all require a valid session

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/parties` | Add a party. Body `{name, size, phone?, note?}`. Returns the full party including `token` and `quoted_wait_minutes`. |
| GET | `/api/parties?status=active\|all&date=YYYY-MM-DD` | The queue. Defaults to `active`. Active parties are ordered by `joined_at` ascending. |
| GET | `/api/parties/{id}` | One party, full detail. |
| POST | `/api/parties/{id}/notify` | `WAITING → NOTIFIED`, stamps `notified_at`. |
| POST | `/api/parties/{id}/seat` | `WAITING\|NOTIFIED → SEATED`, stamps `seated_at` and `closed_at`. Feeds the estimator. |
| POST | `/api/parties/{id}/no-show` | `NOTIFIED → NO_SHOW`. |
| POST | `/api/parties/{id}/cancel` | `WAITING\|NOTIFIED → CANCELLED`. |
| GET | `/api/stats?date=YYYY-MM-DD` | Today's summary: parties seated, guests seated (sum of `size`), average actual wait, median actual wait, no-show count, cancellation count, and quote accuracy (mean absolute error between `quoted_wait_minutes` and actual turnaround). |
| GET | `/api/config` | Current settings. |
| PUT | `/api/config` | Update settings. |

Party responses to the host include every field, `token` included, so the console can render the guest link and its QR code.

### 8.3 Public — no auth

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/waitlist/{token}` | The guest's own status. |

The response is deliberately minimal:

```json
{
  "restaurant_name": "The Blue Fig",
  "party_first_name": "Dana",
  "size": 4,
  "status": "WAITING",
  "position_in_line": 3,
  "estimated_wait_minutes": 25,
  "joined_at": "2026-09-12T18:04:00Z"
}
```

`position_in_line` is the party's rank **within its own size bucket** among active parties, counting from 1 — the same population the estimate in section 6.3 is derived from, so the two numbers always agree. A party may therefore be told they are 2nd while five other parties are physically waiting. `estimated_wait_minutes` is the live recalculation of section 6.4, not the frozen `quoted_wait_minutes`.

The response exposes no `id`, no phone, no note, and nothing about any other party beyond that position number. An unknown or malformed token returns a generic **404** with no detail, so tokens cannot be probed or enumerated.

## 9. Frontend

React + TypeScript, built against `openapi.yaml` with generated types.

### 9.1 Host console — `/host`

- A password gate. Once authenticated, the session cookie carries the console.
- **Add party** form: name, size, optional phone, optional note. On submit the new party appears at the bottom of the queue and a modal shows the guest link as a QR code plus copyable text, so the host can hand it over immediately.
- **Queue**, ordered by join time, each row showing: name, size, how long they've been waiting (a live counter), current estimate, and status. Notified parties are visually distinct. A row's actions are Notify, Seat, No-show, Cancel — each only shown when the transition is legal for that status.
- A collapsed **today** panel with the `/api/stats` figures.
- A **settings** panel for the section 7 config.
- The queue refetches every 5 seconds, so two hosts on two tablets stay in sync.

### 9.2 Guest page — `/w/{token}`

One large card, readable at arm's length on a phone, which polls `/api/waitlist/{token}` every 5 seconds:

- `WAITING` — restaurant name, "You're 3rd in line", "About 25 minutes", and how long they've been waiting.
- `NOTIFIED` — the whole screen becomes **YOUR TABLE IS READY**, high contrast, with a "please see the host" line.
- `SEATED` / `CANCELLED` / `NO_SHOW` — a short closing message; polling stops.
- An unknown token renders a plain "we couldn't find that waitlist entry" page.

Polling rather than WebSockets: at one restaurant's scale the difference is invisible to users, and there is far less to get wrong.

## 10. Authentication and security

- One shared `STAFF_PASSWORD` from the environment, compared in constant time, establishing a signed `HttpOnly`, `SameSite=Lax` session cookie.
- Every `/api/parties*`, `/api/stats`, and `/api/config` route requires that session. `/api/waitlist/{token}` never does.
- The token is the guest's only credential, so it must be generated with `secrets`, never with `random`, and never derived from `id`, name, or phone.
- Guest responses are minimal by construction (section 8.3) — the endpoint builds its own response model rather than serializing the `Party` row.
- Rate-limit login attempts to blunt password guessing.

## 11. Repository layout

Following the article's structure:

```
AGENTS.md              # instructions for AI coding assistants
openapi.yaml           # API contract
Makefile               # make dev / test / lint / seed
docs/
  spec.md              # this document
backend/
  app/
    main.py            # FastAPI app, router wiring
    db.py              # SQLAlchemy engine and session
    config.py          # settings and environment
    auth.py            # password check, session dependency
    models.py          # SQLAlchemy models
    schemas.py         # Pydantic request/response models
    api/
      auth.py
      parties.py
      waitlist.py      # the public route
      stats.py
      config.py
    services/
      estimator.py     # pure wait-time logic, no DB
      waitlist.py      # queue operations and status transitions
  tests/
frontend/
  src/
    api/               # generated client and types
    pages/{Host,Guest,Login}.tsx
    components/
  tests/
```

Python dependencies are managed with **uv**. The database is SQLite through SQLAlchemy, with `DATABASE_URL` as the only thing standing between it and Postgres later.

**Layering rule:** routers validate and delegate; services own all business rules and status transitions; the estimator is pure. No SQLAlchemy query appears in a router, and no HTTP concept appears in a service.

## 12. Error handling

| Situation | Response |
|---|---|
| Invalid request body (size < 1, missing name) | 422, from Pydantic validation |
| Wrong staff password | 401 |
| Host route without a session | 401 |
| Unknown party `id` on a host route | 404 |
| Unknown or malformed guest token | 404, generic body, no detail |
| Illegal status transition | 409, naming current and attempted status |

Errors share one JSON shape: `{"detail": "..."}`.

## 13. Testing strategy

- **Estimator (unit, pure).** No history returns the configured default; the blend shrinks toward the prior correctly at n = 1, 5, 20; the window keeps only the last N samples; bucket boundaries at sizes 2/3, 4/5, 6/7; the capacity divisor; rounding to 5 minutes; zero parties ahead gives zero.
- **Service (unit, SQLite in memory).** Every legal transition; every illegal transition raises; timestamps are stamped exactly once; queue ordering; `parties_ahead` counts only active parties in the same bucket that joined earlier.
- **API (integration, `TestClient`).** Full happy path — add, notify, seat — asserted through HTTP; each host route rejects an unauthenticated caller; the guest endpoint leaks no field beyond the section 8.3 shape; an unknown token is a plain 404.
- **Frontend (vitest).** The guest card renders each status correctly; the host row shows only the actions legal for its status.
- A `make seed` command loads a realistic day of history so the adaptive estimator can be demonstrated immediately.

## 14. Build order

Following the article's four stages, each ending in something testable:

1. **Specification** — this document, plus `openapi.yaml` and `AGENTS.md`.
2. **Frontend prototype** — both surfaces built against a mocked API client that satisfies `openapi.yaml`. Clickable end to end, no backend.
3. **Backend integration** — real FastAPI routes, estimator, and services over in-memory storage. The frontend switches to the real client.
4. **Persistence** — SQLAlchemy models, SQLite, migrations, and `make seed`.

## 15. Success criteria

The project is done when:

- A host can take a party from the door to seated without leaving `/host`.
- A guest with a link sees their position fall as parties ahead are seated, and sees the ready screen within 5 seconds of the host tapping Notify.
- After seeding a day of history, quotes measurably differ from the cold-start defaults, and `/api/stats` reports quote accuracy.
- Every host route rejects an unauthenticated caller, and the guest endpoint returns only the fields listed in section 8.3.
- `make test` passes, covering the cases in section 13.
- `make dev` brings the whole app up from a clean checkout.

## 16. Possible future work

Not part of this project, recorded so the design doesn't accidentally preclude them: real SMS behind a notifier interface, table inventory with true assignment, reservations alongside walk-ins, multi-venue tenancy with real user accounts, and a Postgres deployment with Docker Compose and CI.
