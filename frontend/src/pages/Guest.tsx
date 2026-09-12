import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getWaitlistEntry } from '../api/client';
import { isApiError } from '../api/errors';
import type { WaitlistEntry } from '../api/types';
import { usePoll } from '../hooks/usePoll';
import { useTicker } from '../hooks/useTicker';
import { clockTime, estimateSentence, minutesSince, ordinal, ordinalSuffix } from '../lib/format';

export default function Guest() {
  const { token = '' } = useParams<{ token: string }>();
  const now = useTicker(15_000);
  const [stopped, setStopped] = useState(false);

  const load = useCallback(() => getWaitlistEntry(token), [token]);
  const { data, error, loading } = usePoll<WaitlistEntry>(load, {
    intervalMs: 5000,
    enabled: !stopped,
  });

  const status = data?.status;
  const called = status === 'NOTIFIED';

  // Nothing changes for a party that has been seated or has left, so stop.
  useEffect(() => {
    if (status && status !== 'WAITING' && status !== 'NOTIFIED') setStopped(true);
  }, [status]);

  // The whole screen changes when a table opens, browser chrome included.
  useEffect(() => {
    const theme = document.querySelector('meta[name="theme-color"]');
    document.body.style.background = called ? '#e3a72f' : '';
    theme?.setAttribute('content', called ? '#e3a72f' : '#101a18');
    return () => {
      document.body.style.background = '';
      theme?.setAttribute('content', '#101a18');
    };
  }, [called]);

  if (error) {
    const missing = isApiError(error) && error.status === 404;
    return (
      <main className="guest">
        <div className="guest-core">
          <p className="guest-closing">
            {missing ? "We couldn't find that waitlist entry." : "We can't reach the front door."}
          </p>
          <p className="guest-closing-line">
            {missing
              ? 'Check the link, or ask the host to add you again.'
              : 'Keep this page open and it will try again on its own.'}
          </p>
        </div>
      </main>
    );
  }

  if (loading || !data) {
    return (
      <main className="guest">
        <p className="guest-loading">Finding your place in line</p>
      </main>
    );
  }

  const waited = minutesSince(data.joined_at, now);

  if (called) {
    const calledLine = 'Come and see the host at the front.';
    return (
      <main className="guest guest-called">
        <p className="guest-venue">{data.restaurant_name}</p>
        <div className="guest-core">
          <p className="guest-ready">Your table is ready</p>
          <p className="guest-ready-line">{calledLine}</p>
          <p className="guest-ready-table">A table for {data.size}, under {data.party_first_name}.</p>
        </div>
        <footer className="guest-foot">
          <span>You waited {waited} minutes.</span>
        </footer>
      </main>
    );
  }

  if (data.status !== 'WAITING') {
    return (
      <main className="guest">
        <p className="guest-venue">{data.restaurant_name}</p>
        <div className="guest-core">
          <p className="guest-closing">{CLOSING[data.status].lead}</p>
          <p className="guest-closing-line">{CLOSING[data.status].line}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="guest">
      <p className="guest-venue">{data.restaurant_name}</p>

      <div className="guest-core">
        <p className="guest-rank" aria-label={`${ordinal(data.position_in_line)} in line`}>
          <span aria-hidden="true">{data.position_in_line}</span>
          <span className="guest-rank-suffix" aria-hidden="true">
            {ordinalSuffix(data.position_in_line)}
          </span>
        </p>
        <p className="guest-rank-line">in line for a table for {data.size}</p>

        <p className="guest-estimate">
          {estimateSentence(data.estimated_wait_minutes)}
          <span className="guest-estimate-note">
            {data.estimated_wait_minutes <= 0
              ? 'Head to the host stand.'
              : 'This drops as the tables ahead of you clear.'}
          </span>
        </p>
      </div>

      <footer className="guest-foot">
        <span>
          {data.party_first_name}, you joined at {clockTime(data.joined_at)}.
        </span>
        <span>Waiting {waited} minutes so far.</span>
      </footer>
    </main>
  );
}

const CLOSING: Record<string, { lead: string; line: string }> = {
  SEATED: { lead: "You're at your table.", line: 'Enjoy your meal.' },
  CANCELLED: {
    lead: "You're off the list.",
    line: 'If that is not right, the host can put you back on.',
  },
  NO_SHOW: {
    lead: 'We called your table and missed you.',
    line: 'Have a word with the host and they will get you back in line.',
  },
};
