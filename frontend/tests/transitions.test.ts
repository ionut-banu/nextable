import { describe, expect, it } from 'vitest';
import { isLegal, legalActions } from '../src/lib/transitions';

describe('legal actions by status', () => {
  it('offers notify, seat and cancel to a waiting party', () => {
    expect(legalActions('WAITING')).toEqual(['notify', 'seat', 'cancel']);
  });

  it('offers seat, no-show and cancel once a party has been called', () => {
    expect(legalActions('NOTIFIED')).toEqual(['seat', 'no-show', 'cancel']);
  });

  it('offers nothing at all from a terminal status', () => {
    expect(legalActions('SEATED')).toEqual([]);
    expect(legalActions('NO_SHOW')).toEqual([]);
    expect(legalActions('CANCELLED')).toEqual([]);
  });

  it('allows a no-show only from NOTIFIED', () => {
    expect(isLegal('NOTIFIED', 'no-show')).toBe(true);
    expect(isLegal('WAITING', 'no-show')).toBe(false);
  });
});
