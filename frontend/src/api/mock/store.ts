/**
 * The mock backend.
 *
 * Everything here disappears when the real FastAPI service lands. It exists so
 * both surfaces can be built and used end to end against the contract in
 * docs/spec.md section 8. State lives in localStorage, so a host tab and a
 * guest tab on the same browser see the same queue as they poll.
 */
import { ApiError } from '../errors';
import type {
  Config,
  CreatePartyInput,
  Party,
  PartyListFilter,
  PartyStatus,
  SizeBucket,
  Stats,
  WaitlistEntry,
} from '../types';
import { bucketForSize, estimateForBucket } from './estimator';
import { ACTION_RESULT, isLegal, type PartyAction } from '../../lib/transitions';
import { buildSeed } from './seed';
import { newToken } from './token';

const STORAGE_KEY = 'nextable.mock.v3';

/** A party row as the mock database holds it: no derived fields. */
export interface StoredParty {
  id: number;
  token: string;
  name: string;
  size: number;
  phone: string | null;
  note: string | null;
  status: PartyStatus;
  quoted_wait_minutes: number;
  joined_at: string;
  notified_at: string | null;
  seated_at: string | null;
  closed_at: string | null;
}

export interface MockState {
  nextId: number;
  parties: StoredParty[];
  config: Config;
  signedIn: boolean;
}

export const DEFAULT_CONFIG: Config = {
  restaurant_name: 'The Blue Fig',
  history_window: 20,
  smoothing_constant: 5,
  buckets: {
    SMALL: { default_turn_minutes: 25, table_count: 8 },
    MEDIUM: { default_turn_minutes: 40, table_count: 6 },
    LARGE: { default_turn_minutes: 55, table_count: 3 },
    XLARGE: { default_turn_minutes: 75, table_count: 1 },
  },
};

/** The prototype's stand-in for STAFF_PASSWORD. */
export const DEMO_PASSWORD = 'bluefig';

let cache: MockState | null = null;

function freshState(): MockState {
  return buildSeed(DEFAULT_CONFIG);
}

export function loadState(): MockState {
  const raw = safeGetItem(STORAGE_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as MockState;
      if (parsed && Array.isArray(parsed.parties) && parsed.config) {
        cache = parsed;
        return parsed;
      }
    } catch {
      // Corrupt state is not worth recovering in a prototype: start over.
    }
  }
  const seeded = cache ?? freshState();
  saveState(seeded);
  return seeded;
}

export function saveState(state: MockState): void {
  cache = state;
  safeSetItem(STORAGE_KEY, JSON.stringify(state));
}

/** Throw away the demo data and reseed. Wired to a control in the host console. */
export function resetState(): MockState {
  const seeded = freshState();
  seeded.signedIn = loadStateSignedIn();
  saveState(seeded);
  return seeded;
}

function loadStateSignedIn(): boolean {
  try {
    return cache?.signedIn ?? false;
  } catch {
    return false;
  }
}

function safeGetItem(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Private browsing, or storage disabled. The in-memory cache still works.
  }
}

// ---------------------------------------------------------------------------
// Derivation
// ---------------------------------------------------------------------------

export function isActive(status: PartyStatus): boolean {
  return status === 'WAITING' || status === 'NOTIFIED';
}

function byJoinTime(a: StoredParty, b: StoredParty): number {
  const diff = Date.parse(a.joined_at) - Date.parse(b.joined_at);
  return diff !== 0 ? diff : a.id - b.id;
}

export function activeParties(state: MockState): StoredParty[] {
  return state.parties.filter((party) => isActive(party.status)).sort(byJoinTime);
}

/** Turnaround minutes for every seated party in a bucket, oldest first. */
export function turnaroundSamples(state: MockState, bucket: SizeBucket): number[] {
  return state.parties
    .filter((party) => party.status === 'SEATED' && party.seated_at !== null)
    .filter((party) => bucketForSize(party.size) === bucket)
    .sort((a, b) => Date.parse(a.seated_at ?? '') - Date.parse(b.seated_at ?? ''))
    .map((party) => minutesBetween(party.joined_at, party.seated_at ?? party.joined_at));
}

/**
 * Active parties in the same bucket that joined strictly earlier (spec 6.3).
 * Ties fall back to insertion order so two parties never claim one position.
 */
function partiesAhead(state: MockState, party: StoredParty): number {
  const bucket = bucketForSize(party.size);
  return activeParties(state).filter(
    (other) => bucketForSize(other.size) === bucket && byJoinTime(other, party) < 0,
  ).length;
}

function liveEstimate(state: MockState, party: StoredParty): number {
  const bucket = bucketForSize(party.size);
  return estimateForBucket(bucket, partiesAhead(state, party), turnaroundSamples(state, bucket), state.config);
}

/** Add the derived fields the host console reads. */
export function toParty(state: MockState, party: StoredParty): Party {
  const active = isActive(party.status);
  return {
    ...party,
    bucket: bucketForSize(party.size),
    current_estimate_minutes: active ? liveEstimate(state, party) : null,
    position_in_line: active ? partiesAhead(state, party) + 1 : null,
  };
}

export function toWaitlistEntry(state: MockState, party: StoredParty): WaitlistEntry {
  const active = isActive(party.status);
  return {
    restaurant_name: state.config.restaurant_name,
    party_first_name: firstName(party.name),
    size: party.size,
    status: party.status,
    position_in_line: active ? partiesAhead(state, party) + 1 : 0,
    estimated_wait_minutes: active ? liveEstimate(state, party) : 0,
    joined_at: party.joined_at,
  };
}

function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? name;
}

// ---------------------------------------------------------------------------
// Writes
// ---------------------------------------------------------------------------

export function createParty(state: MockState, input: CreatePartyInput, now: Date): StoredParty {
  const name = input.name.trim();
  if (!name) throw new ApiError(422, 'A party needs a name.');
  if (!Number.isInteger(input.size) || input.size < 1) {
    throw new ApiError(422, 'Party size must be a whole number of 1 or more.');
  }

  const bucket = bucketForSize(input.size);
  const party: StoredParty = {
    id: state.nextId,
    token: newToken(),
    name,
    size: input.size,
    phone: emptyToNull(input.phone),
    note: emptyToNull(input.note),
    status: 'WAITING',
    // Counted before this party joins the queue, then frozen for good.
    quoted_wait_minutes: estimateForBucket(
      bucket,
      activeParties(state).filter((other) => bucketForSize(other.size) === bucket).length,
      turnaroundSamples(state, bucket),
      state.config,
    ),
    joined_at: now.toISOString(),
    notified_at: null,
    seated_at: null,
    closed_at: null,
  };

  state.nextId += 1;
  state.parties.push(party);
  return party;
}

/**
 * Apply a status transition, or reject it.
 *
 * This is the mock's copy of the service-layer rule: an illegal transition is
 * a 409 naming the current and the attempted status, never a silent no-op.
 */
export function applyAction(
  state: MockState,
  id: number,
  action: PartyAction,
  now: Date,
): StoredParty {
  const party = state.parties.find((candidate) => candidate.id === id);
  if (!party) throw new ApiError(404, 'That party is not on the list.');

  if (!isLegal(party.status, action)) {
    throw new ApiError(
      409,
      `Cannot ${action} a party that is ${party.status}. It would have to become ${ACTION_RESULT[action]}.`,
    );
  }

  const stamp = now.toISOString();
  party.status = ACTION_RESULT[action];

  if (action === 'notify') {
    party.notified_at = stamp;
  } else {
    if (action === 'seat') party.seated_at = stamp;
    party.closed_at = stamp;
  }

  return party;
}

export function listParties(state: MockState, filter: PartyListFilter, date?: string): StoredParty[] {
  const parties =
    filter === 'active'
      ? activeParties(state)
      : [...state.parties].sort((a, b) => byJoinTime(b, a));

  if (!date) return parties;
  return parties.filter((party) => localDate(party.joined_at) === date);
}

export function computeStats(state: MockState, date: string): Stats {
  const onDate = state.parties.filter((party) => localDate(party.joined_at) === date);
  const seated = onDate.filter((party) => party.status === 'SEATED' && party.seated_at);

  const waits = seated.map((party) => minutesBetween(party.joined_at, party.seated_at ?? party.joined_at));
  const errors = seated.map((party) =>
    Math.abs(party.quoted_wait_minutes - minutesBetween(party.joined_at, party.seated_at ?? party.joined_at)),
  );

  return {
    date,
    parties_seated: seated.length,
    guests_seated: seated.reduce((total, party) => total + party.size, 0),
    average_wait_minutes: mean(waits),
    median_wait_minutes: median(waits),
    no_show_count: onDate.filter((party) => party.status === 'NO_SHOW').length,
    cancelled_count: onDate.filter((party) => party.status === 'CANCELLED').length,
    quote_accuracy_minutes: mean(errors),
  };
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

export function minutesBetween(from: string, to: string): number {
  return Math.max(0, Math.round((Date.parse(to) - Date.parse(from)) / 60000));
}

export function localDate(iso: string): string {
  const date = new Date(iso);
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

export function today(): string {
  return localDate(new Date().toISOString());
}

function mean(values: number[]): number | null {
  if (values.length === 0) return null;
  return Math.round(values.reduce((total, value) => total + value, 0) / values.length);
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  const value =
    sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
  return Math.round(value);
}

function emptyToNull(value: string | null | undefined): string | null {
  const trimmed = (value ?? '').trim();
  return trimmed === '' ? null : trimmed;
}

