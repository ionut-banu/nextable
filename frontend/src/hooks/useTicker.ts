import { useEffect, useState } from 'react';

/** A clock that re-renders its consumer, for the live "waiting 18 min" counters. */
export function useTicker(intervalMs = 15_000): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);

  return now;
}
