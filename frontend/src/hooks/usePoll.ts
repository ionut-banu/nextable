import { useCallback, useEffect, useRef, useState } from 'react';

export interface PollResult<T> {
  data: T | null;
  error: unknown;
  loading: boolean;
  refresh: () => Promise<void>;
}

/**
 * Read something from the API now, then every `intervalMs` (spec 9: both
 * surfaces poll every 5 seconds). Two hosts on two tablets converge within one
 * interval, which is the whole reason the queue is polled rather than cached.
 */
export function usePoll<T>(
  load: () => Promise<T>,
  { intervalMs = 5000, enabled = true }: { intervalMs?: number; enabled?: boolean } = {},
): PollResult<T> {
  const loadRef = useRef(load);
  loadRef.current = load;

  const mounted = useRef(true);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const next = await loadRef.current();
      if (!mounted.current) return;
      setData(next);
      setError(null);
    } catch (caught) {
      if (mounted.current) setError(caught);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs, refresh]);

  return { data, error, loading, refresh };
}
