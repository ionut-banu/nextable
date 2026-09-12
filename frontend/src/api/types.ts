/**
 * The API contract, mirroring docs/spec.md section 8.
 *
 * These types are hand-written for the frontend prototype. Once the backend
 * exists they are replaced by types generated from openapi.yaml — see the
 * layering rules in AGENTS.md.
 */

export type PartyStatus = 'WAITING' | 'NOTIFIED' | 'SEATED' | 'NO_SHOW' | 'CANCELLED';

export type SizeBucket = 'SMALL' | 'MEDIUM' | 'LARGE' | 'XLARGE';

/** A party as the host console sees it: every field, token included. */
export interface Party {
  id: number;
  token: string;
  name: string;
  size: number;
  phone: string | null;
  note: string | null;
  status: PartyStatus;
  bucket: SizeBucket;
  /** The quote given at join time. Frozen — never updated. */
  quoted_wait_minutes: number;
  /**
   * The live estimate for this party as the queue stands now (spec 6.4).
   * Null once the party reaches a terminal status.
   */
  current_estimate_minutes: number | null;
  /** Rank within this party's own size bucket among active parties, from 1. */
  position_in_line: number | null;
  joined_at: string;
  notified_at: string | null;
  seated_at: string | null;
  closed_at: string | null;
}

export interface CreatePartyInput {
  name: string;
  size: number;
  phone?: string | null;
  note?: string | null;
}

/** The guest's own status. Deliberately minimal — spec 8.3. */
export interface WaitlistEntry {
  restaurant_name: string;
  party_first_name: string;
  size: number;
  status: PartyStatus;
  position_in_line: number;
  estimated_wait_minutes: number;
  joined_at: string;
}

export interface BucketConfig {
  default_turn_minutes: number;
  table_count: number;
}

export interface Config {
  restaurant_name: string;
  history_window: number;
  smoothing_constant: number;
  buckets: Record<SizeBucket, BucketConfig>;
}

export interface Stats {
  date: string;
  parties_seated: number;
  guests_seated: number;
  average_wait_minutes: number | null;
  median_wait_minutes: number | null;
  no_show_count: number;
  cancelled_count: number;
  /** Mean absolute error between the frozen quote and the real turnaround. */
  quote_accuracy_minutes: number | null;
}

export type PartyListFilter = 'active' | 'all';
