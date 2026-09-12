import { describe, expect, it } from 'vitest';
import {
  bucketForSize,
  effectiveTurnMinutes,
  estimateWaitMinutes,
} from '../src/api/mock/estimator';
import type { BucketConfig } from '../src/api/types';

const SMALL: BucketConfig = { default_turn_minutes: 25, table_count: 8 };
const LARGE: BucketConfig = { default_turn_minutes: 55, table_count: 3 };

const N = 20;
const M = 5;

function quote(partiesAhead: number, samples: number[], bucketConfig: BucketConfig) {
  return estimateWaitMinutes({
    partiesAhead,
    samples,
    bucketConfig,
    historyWindow: N,
    smoothingConstant: M,
  });
}

describe('size buckets', () => {
  it('splits on the boundaries in the spec', () => {
    expect(bucketForSize(1)).toBe('SMALL');
    expect(bucketForSize(2)).toBe('SMALL');
    expect(bucketForSize(3)).toBe('MEDIUM');
    expect(bucketForSize(4)).toBe('MEDIUM');
    expect(bucketForSize(5)).toBe('LARGE');
    expect(bucketForSize(6)).toBe('LARGE');
    expect(bucketForSize(7)).toBe('XLARGE');
    expect(bucketForSize(24)).toBe('XLARGE');
  });
});

describe('effective turn time', () => {
  it('is exactly the configured default with no history', () => {
    expect(effectiveTurnMinutes([], SMALL, N, M)).toBe(25);
  });

  it('shrinks toward the prior as samples arrive', () => {
    // (n * observed + m * prior) / (n + m), prior 25, m 5, every sample 55.
    expect(effectiveTurnMinutes([55], SMALL, N, M)).toBe(30);
    expect(effectiveTurnMinutes(Array(5).fill(55), SMALL, N, M)).toBe(40);
    expect(effectiveTurnMinutes(Array(20).fill(55), SMALL, N, M)).toBe(49);
  });

  it('keeps only the last N samples', () => {
    const withOldOutliers = [...Array(5).fill(200), ...Array(20).fill(55)];
    expect(effectiveTurnMinutes(withOldOutliers, SMALL, N, M)).toBe(49);
  });
});

describe('the quote', () => {
  it('is zero when nobody is ahead', () => {
    expect(quote(0, [], SMALL)).toBe(0);
    expect(quote(0, Array(20).fill(90), LARGE)).toBe(0);
  });

  it('divides by the tables in play', () => {
    // 1 to 8 ahead is one turn; 9 is two.
    expect(quote(1, [], SMALL)).toBe(25);
    expect(quote(8, [], SMALL)).toBe(25);
    expect(quote(9, [], SMALL)).toBe(50);
  });

  it('rounds up to the nearest five minutes', () => {
    // Prior 25 blended with a single 28 gives 25.5, which displays as 30.
    expect(quote(1, [28], SMALL)).toBe(30);
  });

  it('uses learned turnarounds once they exist', () => {
    const cold = quote(3, [], LARGE);
    const learned = quote(3, Array(20).fill(80), LARGE);
    expect(cold).toBe(55);
    expect(learned).toBeGreaterThan(cold);
  });
});
