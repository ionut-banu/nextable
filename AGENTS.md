# AGENTS.md

Working agreement for AI coding assistants on **Nextable**, a restaurant waitlist manager. Read this before touching code.

## 1. The spec is the source of truth

[docs/spec.md](docs/spec.md) is an approved specification. It is precise on purpose, especially section 6 (wait estimation) and section 8 (API contract).

- Implement what the spec says. Do not improvise fields, routes, statuses, or formulas.
- If the spec is ambiguous or looks wrong, **stop and ask**. Do not silently pick an interpretation.
- If a change to behaviour is agreed, update `docs/spec.md` in the same change that implements it. The spec must never lag the code.
- Section 3 lists non-goals. They are deliberate omissions. Do not add SMS, table records, reservations, multi-tenancy, user accounts, or i18n "while you're in there".

## 2. Build order

Work follows the four stages in § 14, each ending in something testable:

1. **Specification** — `docs/spec.md`, `openapi.yaml`, this file.
2. **Frontend prototype** — both surfaces against a mocked API client that satisfies `openapi.yaml`. Clickable end to end, no backend.
3. **Backend integration** — real FastAPI routes, estimator and services over in-memory storage. The frontend switches to the real client.
4. **Persistence** — SQLAlchemy models, SQLite, migrations, `make seed`.

Do not start a later stage before the earlier one is complete and testable.

## 3. Architecture rules

These are not style preferences. A change that breaks one of them is wrong.

- **Routers validate and delegate.** No SQLAlchemy query and no business rule in `app/api/*`.
- **Services own the rules.** Every status transition is enforced in `app/services/waitlist.py`, never in a router and never in the frontend. An illegal transition raises, and surfaces as **409** naming the current and the attempted status. It must never be a silent no-op.
- **The estimator is pure.** `app/services/estimator.py` takes a bucket, a list of turnaround samples, a count of parties ahead, and the config, and returns an integer. No database access, no clock reads, no imports from `app.models` or `app.db`. This is what makes it exhaustively unit-testable.
- **No HTTP concepts in a service.** Services raise domain errors; the API layer maps them to status codes.
- All timestamps are **UTC**, stored and returned as ISO-8601.

## 4. Status lifecycle

```
WAITING ──notify──> NOTIFIED ──seat──> SEATED      (terminal)
   │                    │
   │                    ├──no-show──>  NO_SHOW     (terminal)
   │                    └──cancel──>   CANCELLED   (terminal)
   ├──seat────────────────────────────> SEATED     (terminal)
   └──cancel──────────────────────────> CANCELLED  (terminal)
```

- `NO_SHOW` is reachable **only** from `NOTIFIED`. A party never called cannot be a no-show — cancel it instead.
- Terminal statuses are final; any transition out of one is rejected.
- A party is **active** when `WAITING` or `NOTIFIED`. Active parties are the queue.
- Each timestamp (`notified_at`, `seated_at`, `closed_at`) is stamped exactly once.

## 5. Wait estimation invariants

- `quoted_wait_minutes` is **frozen** at join time and never updated. It exists only to score accuracy in `/api/stats`.
- The estimate shown to a waiting guest is **recomputed on every read**, so positions and times fall as parties ahead are seated.
- `parties_ahead` counts only **active** parties **in the same bucket** that joined **strictly earlier**.
- `position_in_line` on the guest page is the rank within that same population, counting from 1 — so the position and the estimate always agree. A party may be told they are 2nd while five other parties are physically waiting. This is intended; do not "fix" it.
- Quotes round up to the nearest 5 minutes for display. A quote of 0 means "we can seat you now".

## 6. Security rules

Non-negotiable, because the guest token is a bearer credential.

- Generate tokens with `secrets.token_urlsafe(16)`. **Never** `random`, never derived from `id`, name, or phone.
- `/api/waitlist/{token}` builds its **own** response model. Never serialize a `Party` row to a guest. The response carries exactly the fields in § 8.3 — no `id`, no phone, no note, nothing about any other party beyond the position number.
- An unknown or malformed token returns a generic **404** with no detail, so tokens cannot be probed or enumerated.
- Every `/api/parties*`, `/api/stats`, and `/api/config` route requires a valid session. `/api/waitlist/{token}` never does.
- Compare the staff password in constant time. The session cookie is signed, `HttpOnly`, `SameSite=Lax`.
- `STAFF_PASSWORD`, `SESSION_SECRET`, and `DATABASE_URL` come from the environment. Never commit secrets, never hard-code a default password, never log a password or a token.
- Rate-limit login attempts.

## 7. Errors

One JSON shape everywhere: `{"detail": "..."}`.

| Situation | Response |
|---|---|
| Invalid request body (size < 1, missing name) | 422, from Pydantic |
| Wrong staff password | 401 |
| Host route without a session | 401 |
| Unknown party `id` on a host route | 404 |
| Unknown or malformed guest token | 404, generic body |
| Illegal status transition | 409, naming current and attempted status |

## 8. Testing

Write the test with the change, not after. `make test` must pass before you call anything done — run it and read the output; do not assume.

- **Estimator (unit, pure).** No history returns the configured default; the blend shrinks correctly at n = 1, 5, 20; the window keeps only the last N; bucket boundaries at sizes 2/3, 4/5, 6/7; the capacity divisor; rounding to 5 minutes; zero parties ahead gives zero.
- **Service (unit, SQLite in memory).** Every legal transition; every illegal transition raises; timestamps stamped exactly once; queue ordering; `parties_ahead` counts only active same-bucket parties that joined earlier.
- **API (integration, `TestClient`).** The happy path add → notify → seat asserted through HTTP; every host route rejects an unauthenticated caller; the guest endpoint leaks no field beyond § 8.3; an unknown token is a plain 404.
- **Frontend (vitest).** The guest card renders each status; a host row shows only the actions legal for its status.

Hand-seed test data. Do not let a test depend on wall-clock timing.

## 9. Conventions

- **Python** dependencies with **uv**. Type hints throughout. Pydantic models for every request and response body.
- **Frontend** React + TypeScript. API types are **generated** from `openapi.yaml` into `frontend/src/api/` — do not hand-edit generated files and do not hand-write a duplicate type.
- `openapi.yaml` and the implementation must agree. Change the contract first.
- Both surfaces poll every 5 seconds. No WebSockets — at one restaurant's scale the difference is invisible and there is far less to get wrong.
- Match the surrounding code's naming and comment density. Comments explain *why*, not *what*.

## 10. Commands

```bash
make dev      # run backend and frontend
make test     # all tests
make lint     # lint and format checks
make seed     # load a realistic day of history for the estimator demo
```

## 11. Done means

- `make test` passes, covering § 13 of the spec.
- `make dev` brings the app up from a clean checkout.
- The spec still describes the code.
- No secret, token, or password appears in the repo or in a log line.
