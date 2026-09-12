# Nextable

**Restaurant waitlist manager.** Replaces the paper list and the buzzer at a restaurant's front door.

A host adds walk-in parties to a queue, the app quotes each party a wait time that gets more accurate as the restaurant serves more guests, and each party gets a private link showing their live position. When a table opens, the host taps **Notify** and the guest's phone turns into a full-screen "your table is ready" card.

The name is "next" + "table" — the next available table.

Built for the AI Dev Tools Zoomcamp 2026 (homework 02).

## Status: specification

Nothing is implemented yet. The approved specification is [docs/spec.md](docs/spec.md), and implementation will follow its four stages:

1. **Specification** — the spec, the API contract, and the agent instructions.
2. **Frontend prototype** — both surfaces against a mocked API, clickable end to end.
3. **Backend integration** — real routes and wait-time logic.
4. **Persistence** — a database and a seed command.

This README will grow setup and usage instructions as those stages land. Until then the spec is the place to look.

## Scope

Two surfaces: a **host console** at `/host` behind a shared staff password, and a **guest status page** at `/w/{token}` where the link itself is the credential.

Walk-ins only, one restaurant, and no real SMS — the app is fully demonstrable offline, with no third-party accounts, no API keys, and no per-message costs. [Section 3 of the spec](docs/spec.md) lists what is deliberately out of scope.

Python and FastAPI on the backend, React and TypeScript on the frontend, SQLite for storage.

## Documentation

- [docs/spec.md](docs/spec.md) — the full specification and the source of truth.
- [AGENTS.md](AGENTS.md) — working agreement for AI coding assistants.
