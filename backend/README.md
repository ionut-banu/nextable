# Nextable backend

Stage 3 of [the build order](../docs/spec.md): real FastAPI routes, services and estimator over in-memory storage. Stage 4 replaces that storage with SQLAlchemy and SQLite.

## Running it

```bash
cp .env.example .env          # then change the password
uv sync
uv run pytest                 # 95 tests
uv run uvicorn app.main:app --reload --port 8000
```

Interactive docs at http://localhost:8000/docs. The frontend dev server on port 5173 is already allowed through CORS with credentials.

Environment, never in the database (spec 7):

| Variable | Purpose |
|---|---|
| `STAFF_PASSWORD` | The one shared host-console password |
| `SESSION_SECRET` | Signs the session cookie |
| `DATABASE_URL` | Unused until stage 4 |

## The database is a mock

[app/db.py](app/db.py) is an in-memory `Database` with the shape a SQLAlchemy session will have: it hands out records, never rows. It is a FastAPI dependency, so tests inject a fresh one per test and stage 4 swaps the body of that module without touching a router or a service.

State lives in the process. Restarting the server empties the queue.

## Layering

The rule from [AGENTS.md](../AGENTS.md), which the structure enforces rather than merely documents:

| Layer | Owns | Never contains |
|---|---|---|
| `app/api/*` | Validation, status codes, response shaping | SQLAlchemy queries, business rules |
| `app/services/waitlist.py` | Queue operations, every status transition | Any HTTP concept |
| `app/services/estimator.py` | Spec section 6, and nothing else | Database access, clock reads |

Services raise `PartyNotFound` and `IllegalTransition` from [app/services/errors.py](app/services/errors.py). Those become 404 and 409 in exactly one place — the exception handlers in [app/main.py](app/main.py) — so no service knows what a status code is. Every error body is `{"detail": "..."}`.

## Tests

Written before the code they cover, each one watched failing first.

| File | Covers |
|---|---|
| `test_estimator.py` | Bucket boundaries, the shrinkage blend at n = 1, 5, 20, the N-sample window, the capacity divisor, rounding to five minutes |
| `test_auth.py` | Session cookie flags, forged cookies, the login rate limit |
| `test_parties.py` | Adding, listing, reading, validation, the frozen quote against the live estimate |
| `test_transitions.py` | Every legal transition, and every illegal one refused with a 409 that leaves the record untouched |
| `test_waitlist.py` | The guest response carries exactly seven fields and leaks nothing; unknown and malformed tokens are the same bare 404 |
| `test_stats.py` | Counts, average and median wait, quote accuracy, the day boundary |
| `test_config.py` | Defaults, edits, and a changed table count moving the next quote |

Warnings are errors (`filterwarnings = ["error"]`), with one exact third-party ignore for a deprecation raised inside starlette.

## The contract

`openapi.yaml` at the repository root is generated from this app, as spec section 8 prescribes. Regenerate it after changing any route:

```bash
uv run python scripts/export_openapi.py
```
