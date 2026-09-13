# Nextable backend

FastAPI, SQLAlchemy, and a database chosen by `DATABASE_URL`.

## Running it

```bash
cp .env.example .env               # then change the password
uv sync
uv run alembic upgrade head        # create the schema
uv run python scripts/seed.py      # optional: an evening already in progress
uv run uvicorn app.main:app --reload --port 8000
```

The app refuses to start against a database with no schema and tells you to migrate, rather than failing on the first request.

Interactive docs at http://localhost:8000/docs. The frontend dev server on port 5173 is already allowed through CORS with credentials.

Environment, never in the database (spec 7):

| Variable | Purpose |
|---|---|
| `STAFF_PASSWORD` | The one shared host-console password |
| `SESSION_SECRET` | Signs the session cookie |
| `DATABASE_URL` | Any URL SQLAlchemy understands; defaults to local SQLite |

## The database

[app/db.py](app/db.py) holds the engine, the session factory, and `Database` — a repository over one session. It is the only module that imports SQLAlchemy. Routers and services call the same methods they called when the store was a dictionary, which is why swapping it changed nothing above this layer.

One session per request, opened by the `get_db` dependency: commit if the handler returns, roll back if it raises. A 409 therefore leaves nothing half-written.

### Staying database-agnostic

Nothing in the schema is dialect-specific:

- Statuses and buckets are `VARCHAR` with a `CHECK` constraint, not native enums, so adding one later is an ordinary migration.
- Every timestamp goes through `UtcDateTime`, which refuses naive datetimes on the way in and returns aware UTC on the way out. SQLite has no timezone type, so without this a value would come back naive and compare wrongly.
- Date filtering uses a half-open range rather than a date function, because every backend spells those differently.
- SQLite gets two connection settings it needs; nothing else branches on the dialect.

Moving to Postgres is a driver (`psycopg`), a `DATABASE_URL`, and `alembic upgrade head`.

### Migrations

```bash
uv run alembic upgrade head                              # apply
uv run alembic revision --autogenerate -m "what changed" # after editing models
uv run alembic check                                     # models and schema still agree?
```

`alembic check` also runs as a test, so models and migrations cannot drift apart unnoticed.

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
| `test_persistence.py` | Records outlive their session, a failed request writes nothing, the unique token and size constraints bite, naive datetimes are refused, and the schema stays portable |
| `test_migrations.py` | A migrated database matches the models exactly |

Each test gets a private in-memory database and its own session, injected in place of `get_db`.

Warnings are errors (`filterwarnings = ["error"]`), with one exact third-party ignore for a deprecation raised inside starlette. That setting has already caught a leaked connection and a deprecated test dependency.

## The contract

`openapi.yaml` at the repository root is generated from this app, as spec section 8 prescribes. Regenerate it after changing any route:

```bash
uv run python scripts/export_openapi.py
```
