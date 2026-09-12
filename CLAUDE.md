# CLAUDE.md

All project instructions live in [AGENTS.md](AGENTS.md). **Read it before touching code** — it covers the spec-first rule, the build order, the layering and purity rules, the status lifecycle, the estimator invariants, the security rules around guest tokens, testing, and conventions.

The approved specification is [docs/spec.md](docs/spec.md) and is the source of truth. If the spec and the code disagree, the spec wins until a change to it is agreed and written down.

Quick reminders, all expanded in [AGENTS.md](AGENTS.md):

- Routers validate and delegate; services own every business rule and status transition; `services/estimator.py` is pure — no DB, no clock.
- An illegal status transition is a **409**, never a silent no-op.
- The guest endpoint builds its own minimal response model and returns a generic 404 for an unknown token. Never serialize a `Party` row to a guest.
- Section 3 of the spec lists non-goals. They are deliberate — do not implement them.
- Run `make test` and read the output before calling anything done.
