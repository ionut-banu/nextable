# Nextable frontend

Stage 2 of [the build order](../docs/spec.md): both surfaces, clickable end to end, with no backend behind them.

## Running it

```bash
npm install
npm run dev      # http://localhost:5173/host
npm run test     # estimator and transition rules
npm run build    # typecheck, then a production build
```

The host console is at `/host`. The prototype's staff password is **bluefig**. A guest page lives at `/w/{token}`; the quickest way to reach one is to add a party and use **Open guest view** in the dialog that appears, or the **Guest link** button on any row.

Open the guest page in a second window next to the console. Both poll every five seconds and share one store, so tapping **Notify** turns the guest screen brass within five seconds — the demo the spec asks for.

## Where the backend will plug in

Every call to the backend goes through [src/api/client.ts](src/api/client.ts) and nowhere else. Each function is named and shaped after a route in section 8 of the spec. When the real service exists, the bodies become `fetch` calls and nothing above that file changes.

Behind it, [src/api/mock/](src/api/mock/) is a small in-browser stand-in for the backend, and all of it is throwaway:

| File | Stands in for | Notes |
|---|---|---|
| `store.ts` | `services/waitlist.py` and the database | State in `localStorage`, so a host tab and a guest tab see one queue. Enforces the status transitions and raises the same 409s. |
| `estimator.ts` | `services/estimator.py` | Pure. A port of spec section 6, kept honest by `tests/estimator.test.ts`. |
| `seed.ts` | `make seed` | An evening already in progress, so the estimator has real turnarounds to blend from the first click. |

Deleting that directory and rewriting the bodies in `client.ts` is the whole of the stage 3 frontend change.

## Structure

```
src/
  api/        client.ts (the only backend boundary), types.ts, mock/
  components/ AddPartyForm, QueueRow, GuestLinkSheet, TodayPanel, SettingsPanel, Toast
  pages/      Host.tsx, Guest.tsx, Login.tsx
  hooks/      usePoll (the 5-second refresh), useTicker (live wait counters)
  lib/        transitions.ts (which actions a status allows), format.ts
  styles/     tokens.css, base.css, host.css, guest.css
tests/        estimator and transition rules, run with vitest
```

## What is not real yet

- The API types in `src/api/types.ts` are hand-written against the spec. They are replaced by types generated from `openapi.yaml` once that file exists.
- There is no session cookie. The mock keeps a `signedIn` flag in the same store, and every host call checks it, so the 401 paths behave — but the password is compared in the browser and is not a security boundary.
- Component render tests are not written yet; the two suites that exist cover the pure rules.
