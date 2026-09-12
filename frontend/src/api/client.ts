/**
 * The one place the app talks to the backend.
 *
 * Every call the two surfaces make goes through this module and nowhere else.
 * Today each method is served by the in-browser mock in ./mock; when the real
 * service exists, the bodies become fetch calls against the same signatures
 * and nothing above this file changes.
 */
import { ApiError } from './errors';
import type {
  Config,
  CreatePartyInput,
  Party,
  PartyListFilter,
  Stats,
  WaitlistEntry,
} from './types';
import type { PartyAction } from '../lib/transitions';
import {
  DEMO_PASSWORD,
  applyAction,
  computeStats,
  createParty as createInStore,
  listParties as listFromStore,
  loadState,
  resetState,
  saveState,
  toParty,
  toWaitlistEntry,
  today,
} from './mock/store';

/** Enough delay that optimistic UI and loading states are real, not theatre. */
const LATENCY_MS = 90;

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
}

function requireSession(): void {
  if (!loadState().signedIn) {
    throw new ApiError(401, 'Sign in to use the host console.');
  }
}

// ---------------------------------------------------------------------------
// Auth — spec 8.1
// ---------------------------------------------------------------------------

export async function login(password: string): Promise<void> {
  await delay();
  if (password !== DEMO_PASSWORD) {
    throw new ApiError(401, 'That password is not right.');
  }
  const state = loadState();
  state.signedIn = true;
  saveState(state);
}

export async function logout(): Promise<void> {
  await delay();
  const state = loadState();
  state.signedIn = false;
  saveState(state);
}

export async function me(): Promise<void> {
  await delay();
  requireSession();
}

// ---------------------------------------------------------------------------
// Host — spec 8.2, all require a session
// ---------------------------------------------------------------------------

export async function createParty(input: CreatePartyInput): Promise<Party> {
  await delay();
  requireSession();
  const state = loadState();
  const stored = createInStore(state, input, new Date());
  saveState(state);
  return toParty(state, stored);
}

export async function listParties(
  filter: PartyListFilter = 'active',
  date?: string,
): Promise<Party[]> {
  await delay();
  requireSession();
  const state = loadState();
  return listFromStore(state, filter, date).map((party) => toParty(state, party));
}

export async function getParty(id: number): Promise<Party> {
  await delay();
  requireSession();
  const state = loadState();
  const party = state.parties.find((candidate) => candidate.id === id);
  if (!party) throw new ApiError(404, 'That party is not on the list.');
  return toParty(state, party);
}

/** notify, seat, no-show and cancel share one implementation (spec 8.2). */
export async function actOnParty(id: number, action: PartyAction): Promise<Party> {
  await delay();
  requireSession();
  const state = loadState();
  const stored = applyAction(state, id, action, new Date());
  saveState(state);
  return toParty(state, stored);
}

export async function getStats(date: string = today()): Promise<Stats> {
  await delay();
  requireSession();
  return computeStats(loadState(), date);
}

export async function getConfig(): Promise<Config> {
  await delay();
  requireSession();
  return structuredClone(loadState().config);
}

export async function updateConfig(config: Config): Promise<Config> {
  await delay();
  requireSession();
  const state = loadState();
  state.config = structuredClone(config);
  saveState(state);
  return structuredClone(state.config);
}

// ---------------------------------------------------------------------------
// Public — spec 8.3, never authenticated
// ---------------------------------------------------------------------------

export async function getWaitlistEntry(token: string): Promise<WaitlistEntry> {
  await delay();
  const state = loadState();
  const party = state.parties.find((candidate) => candidate.token === token);
  // Generic 404 with no detail: an unknown token must not be distinguishable
  // from a malformed one, or tokens can be probed (spec 8.3).
  if (!party) throw new ApiError(404, 'Not found');
  return toWaitlistEntry(state, party);
}

// ---------------------------------------------------------------------------
// Prototype-only escape hatch, removed with the mock
// ---------------------------------------------------------------------------

export async function resetDemoData(): Promise<void> {
  await delay();
  requireSession();
  resetState();
}

export { DEMO_PASSWORD };
