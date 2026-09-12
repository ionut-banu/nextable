# Nextable

**Restaurant waitlist manager.** Replaces the paper list and the buzzer at a restaurant's front door.

A host adds walk-in parties to a queue, the app quotes each party a wait time that gets more accurate as the restaurant serves more guests, and each party gets a private link showing their live position. When a table opens, the host taps **Notify** and the guest's phone turns into a full-screen "your table is ready" card.

The name is "next" + "table" — the next available table.

Built for the AI Dev Tools Zoomcamp 2026 (homework 02).

---

## Status

The specification is approved; implementation follows the four stages in [docs/spec.md § 14](docs/spec.md):

| Stage | What it delivers | Status |
|---|---|---|
| 1. Specification | `docs/spec.md`, `openapi.yaml`, `AGENTS.md` | in progress |
| 2. Frontend prototype | Both surfaces against a mocked API client, clickable end to end | not started |
| 3. Backend integration | Real FastAPI routes, estimator and services over in-memory storage | not started |
| 4. Persistence | SQLAlchemy models, SQLite, migrations, `make seed` | not started |

## The two surfaces

| Surface | Route | Who | Auth |
|---|---|---|---|
| Host console | `/host` | Front-of-house staff, on a tablet at the door | Shared staff password |
| Guest status page | `/w/{token}` | A waiting party, on their own phone | None — the token is the credential |

The host runs an entire service from one screen: add a party, hand over the guest link as a QR code, watch the queue with live wait counters, then Notify, Seat, No-show or Cancel. The guest page is one large card that polls every five seconds and shows position, estimated wait, and — when called — a high-contrast ready screen.

## How the wait estimate works

This is the only real domain logic in the app. Party sizes map to four buckets (`SMALL` 1–2, `MEDIUM` 3–4, `LARGE` 5–6, `XLARGE` 7+), each with a configured default turn time and a table count that acts as a capacity divisor.

For each bucket the app keeps the turnaround times (`seated_at - joined_at`) of the last `N = 20` seated parties and blends them toward the configured prior with a smoothing constant `m = 5`:

```
effective_turn = (n * observed_avg + m * default_turn) / (n + m)
quote_minutes  = ceil(parties_ahead / table_count) * effective_turn
```

With no history the quote is exactly the configured default; as real data arrives the prior fades. That shrinkage is what makes the app sane on its first night and accurate on its tenth. Full rules, including rounding and live recalculation, are in [docs/spec.md § 6](docs/spec.md).

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite (`DATABASE_URL` is the only thing standing between it and Postgres). Dependencies managed with **uv**.
- **Frontend:** React + TypeScript, with API types generated from `openapi.yaml`.
- **Contract first:** `openapi.yaml` is hand-written before the backend exists so the frontend can be built against it. Once the backend is real, FastAPI's generated schema becomes the source of truth.

No third-party accounts, no API keys, no per-message costs — the app is fully demonstrable offline.

## Repository layout

```
AGENTS.md              # instructions for AI coding assistants
CLAUDE.md              # points Claude Code at AGENTS.md
openapi.yaml           # API contract
Makefile               # make dev / test / lint / seed
docs/
  spec.md              # the specification — the source of truth
backend/
  app/
    main.py            # FastAPI app, router wiring
    db.py              # SQLAlchemy engine and session
    config.py          # settings and environment
    auth.py            # password check, session dependency
    models.py          # SQLAlchemy models
    schemas.py         # Pydantic request/response models
    api/               # auth, parties, waitlist, stats, config
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

**Layering rule:** routers validate and delegate; services own all business rules and status transitions; the estimator is pure. No SQLAlchemy query in a router, no HTTP concept in a service.

## Getting started

Once stage 3 lands:

```bash
make dev      # bring the whole app up from a clean checkout
make test     # run backend and frontend tests
make lint     # lint and format checks
make seed     # load a realistic day of history
```

Environment variables (never in the database):

| Variable | Purpose |
|---|---|
| `STAFF_PASSWORD` | The one shared host-console password |
| `SESSION_SECRET` | Signs the session cookie |
| `DATABASE_URL` | SQLite by default |

## Deliberately out of scope

These are omissions, not oversights: real SMS or push notifications, table inventory and assignment, reservations, multi-tenancy, user accounts and roles, POS or payment integration, analytics beyond a single-day summary, and internationalization. See [docs/spec.md § 3](docs/spec.md) and § 16 for what a future version might add.

## Documentation

- [docs/spec.md](docs/spec.md) — the full specification and source of truth.
- [AGENTS.md](AGENTS.md) — working agreements for AI coding assistants.
