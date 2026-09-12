/**
 * Wait estimation, spec section 6.
 *
 * Pure: no storage, no clock, no framework. This mirrors the backend's
 * services/estimator.py and exists only so the prototype can behave like the
 * real thing before that module is written. It is deleted when the backend
 * lands — the frontend must never own this rule.
 */
import type { BucketConfig, Config, SizeBucket } from '../types';

export function bucketForSize(size: number): SizeBucket {
  if (size <= 2) return 'SMALL';
  if (size <= 4) return 'MEDIUM';
  if (size <= 6) return 'LARGE';
  return 'XLARGE';
}

export const BUCKET_ORDER: SizeBucket[] = ['SMALL', 'MEDIUM', 'LARGE', 'XLARGE'];

export const BUCKET_LABELS: Record<SizeBucket, string> = {
  SMALL: 'Tables for 1 to 2',
  MEDIUM: 'Tables for 3 to 4',
  LARGE: 'Tables for 5 to 6',
  XLARGE: 'Tables for 7 or more',
};

/**
 * Blend observed turnarounds toward the configured prior (spec 6.2):
 *   effective_turn = (n * observed_avg + m * default_turn) / (n + m)
 *
 * `samples` are turnaround minutes, most recent last. Only the last
 * `historyWindow` are used.
 */
export function effectiveTurnMinutes(
  samples: readonly number[],
  bucketConfig: BucketConfig,
  historyWindow: number,
  smoothingConstant: number,
): number {
  const window = samples.slice(-Math.max(0, historyWindow));
  const n = window.length;
  const m = smoothingConstant;
  const prior = bucketConfig.default_turn_minutes;

  if (n === 0) return prior;

  const observedAvg = window.reduce((total, value) => total + value, 0) / n;
  return (n * observedAvg + m * prior) / (n + m);
}

/**
 * The quote (spec 6.3):
 *   ceil(parties_ahead / table_count) * effective_turn, rounded up to 5 minutes.
 *
 * Zero parties ahead means zero: we can seat you now.
 */
export function estimateWaitMinutes(args: {
  partiesAhead: number;
  samples: readonly number[];
  bucketConfig: BucketConfig;
  historyWindow: number;
  smoothingConstant: number;
}): number {
  const { partiesAhead, samples, bucketConfig, historyWindow, smoothingConstant } = args;
  if (partiesAhead <= 0) return 0;

  const tableCount = Math.max(1, bucketConfig.table_count);
  const rounds = Math.ceil(partiesAhead / tableCount);
  const turn = effectiveTurnMinutes(samples, bucketConfig, historyWindow, smoothingConstant);
  return roundUpToFive(rounds * turn);
}

export function roundUpToFive(minutes: number): number {
  return Math.ceil(minutes / 5) * 5;
}

/** Convenience for callers that hold a whole Config. */
export function estimateForBucket(
  bucket: SizeBucket,
  partiesAhead: number,
  samples: readonly number[],
  config: Config,
): number {
  return estimateWaitMinutes({
    partiesAhead,
    samples,
    bucketConfig: config.buckets[bucket],
    historyWindow: config.history_window,
    smoothingConstant: config.smoothing_constant,
  });
}
