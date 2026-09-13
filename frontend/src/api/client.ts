/**
 * The one place the app talks to the backend.
 *
 * Every call the two surfaces make goes through this module and nowhere else.
 * Each function is named and shaped after a route in section 8 of the spec.
 *
 * Requests go to the same origin by default: the dev server proxies /api to
 * the backend, so the session cookie is first-party. Point the app at another
 * host with VITE_API_BASE_URL.
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

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

type Method = 'GET' | 'POST' | 'PUT';

interface RequestOptions {
  method?: Method;
  body?: unknown;
  query?: Record<string, string | undefined>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query } = options;

  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, value);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      // The session lives in an HttpOnly cookie, so every call has to carry it.
      credentials: 'include',
      headers: body === undefined ? undefined : { 'content-type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check that the API is running.');
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}

/**
 * Every error the API returns is `{"detail": "..."}` (spec 12). A proxy or a
 * crash can still produce something else, so fall back to the status.
 */
async function toApiError(response: Response): Promise<ApiError> {
  let detail = `The server answered ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') {
      detail = body.detail;
    } else if (Array.isArray(body.detail)) {
      // FastAPI's 422 body is a list of validation problems.
      detail = 'Check the party details and try again.';
    }
  } catch {
    // No JSON body. The status-based message stands.
  }
  return new ApiError(response.status, detail);
}

// ---------------------------------------------------------------------------
// Auth — spec 8.1
// ---------------------------------------------------------------------------

export function login(password: string): Promise<void> {
  return request<void>('/api/auth/login', { method: 'POST', body: { password } });
}

export function logout(): Promise<void> {
  return request<void>('/api/auth/logout', { method: 'POST' });
}

export function me(): Promise<void> {
  return request<void>('/api/auth/me');
}

// ---------------------------------------------------------------------------
// Host — spec 8.2, all require a session
// ---------------------------------------------------------------------------

export function createParty(input: CreatePartyInput): Promise<Party> {
  return request<Party>('/api/parties', {
    method: 'POST',
    body: {
      name: input.name,
      size: input.size,
      phone: input.phone?.trim() || null,
      note: input.note?.trim() || null,
    },
  });
}

export function listParties(
  filter: PartyListFilter = 'active',
  date?: string,
): Promise<Party[]> {
  return request<Party[]>('/api/parties', { query: { status: filter, date } });
}

export function getParty(id: number): Promise<Party> {
  return request<Party>(`/api/parties/${id}`);
}

/** notify, seat, no-show and cancel share one shape (spec 8.2). */
export function actOnParty(id: number, action: PartyAction): Promise<Party> {
  return request<Party>(`/api/parties/${id}/${action}`, { method: 'POST' });
}

export function getStats(date?: string): Promise<Stats> {
  return request<Stats>('/api/stats', { query: { date } });
}

export function getConfig(): Promise<Config> {
  return request<Config>('/api/config');
}

export function updateConfig(config: Config): Promise<Config> {
  return request<Config>('/api/config', { method: 'PUT', body: config });
}

// ---------------------------------------------------------------------------
// Public — spec 8.3, never authenticated
// ---------------------------------------------------------------------------

export function getWaitlistEntry(token: string): Promise<WaitlistEntry> {
  return request<WaitlistEntry>(`/api/waitlist/${encodeURIComponent(token)}`);
}
