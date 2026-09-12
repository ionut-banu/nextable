import { useState } from 'react';
import type { Party } from '../api/types';
import { ACTION_LABELS, legalActions, type PartyAction } from '../lib/transitions';
import { minutesSince, ordinal, shortDuration } from '../lib/format';

const NEEDS_CONFIRMING: PartyAction[] = ['no-show', 'cancel'];

const CONFIRM_QUESTION: Record<string, (name: string) => string> = {
  'no-show': (name) => `Mark ${name} as a no-show? That closes their spot for good.`,
  cancel: (name) => `Take ${name} off the list? That cannot be undone.`,
};

const CONFIRM_BUTTON: Record<string, string> = {
  'no-show': 'Yes, no-show',
  cancel: 'Yes, take them off',
};

export function QueueRow({
  party,
  now,
  busy,
  onAction,
  onShowLink,
}: {
  party: Party;
  now: number;
  busy: boolean;
  onAction: (party: Party, action: PartyAction) => void;
  onShowLink: (party: Party) => void;
}) {
  const [confirming, setConfirming] = useState<PartyAction | null>(null);

  const waited = minutesSince(party.joined_at, now);
  const called = party.status === 'NOTIFIED';
  const calledAgo = party.notified_at ? minutesSince(party.notified_at, now) : 0;

  function handleClick(action: PartyAction) {
    if (NEEDS_CONFIRMING.includes(action) && confirming !== action) {
      setConfirming(action);
      return;
    }
    setConfirming(null);
    onAction(party, action);
  }

  return (
    <li className={called ? 'queue-row queue-row-called' : 'queue-row'}>
      <div className="row-covers numeral">
        <span className="row-covers-number">{party.size}</span>
        {party.position_in_line !== null && (
          <span className="row-rank">{ordinal(party.position_in_line)} of its size</span>
        )}
      </div>

      <div className="row-identity">
        <p className="row-name">{party.name}</p>
        {(party.note || party.phone) && (
          <p className="row-meta">{[party.note, party.phone].filter(Boolean).join(' — ')}</p>
        )}
      </div>

      <div className="row-timing">
        <p>
          <span className="numeral row-waited-number">{waited}</span> min waiting
        </p>
        {called ? (
          <p className="row-timing-second row-timing-called">
            Called {calledAgo === 0 ? 'just now' : `${shortDuration(calledAgo)} ago`}
          </p>
        ) : (
          <p className="row-timing-second">
            {party.current_estimate_minutes === 0
              ? 'Table free now'
              : `About ${party.current_estimate_minutes} min left`}
          </p>
        )}
      </div>

      {confirming ? (
        <div className="row-actions">
          <span className="row-meta">{CONFIRM_QUESTION[confirming](party.name)}</span>
          <button
            className="btn btn-small btn-leave"
            type="button"
            disabled={busy}
            onClick={() => handleClick(confirming)}
          >
            {CONFIRM_BUTTON[confirming]}
          </button>
          <button
            className="btn btn-small btn-quiet"
            type="button"
            onClick={() => setConfirming(null)}
          >
            Keep them waiting
          </button>
        </div>
      ) : (
        <div className="row-actions">
          {legalActions(party.status).map((action) => (
            <button
              key={action}
              type="button"
              className={`btn btn-small ${buttonStyle(action)}`}
              disabled={busy}
              onClick={() => handleClick(action)}
            >
              {ACTION_LABELS[action]}
            </button>
          ))}
          <button className="btn btn-small btn-quiet" type="button" onClick={() => onShowLink(party)}>
            Guest link
          </button>
        </div>
      )}
    </li>
  );
}

function buttonStyle(action: PartyAction): string {
  if (action === 'notify') return 'btn-call';
  if (action === 'seat') return 'btn-solid';
  return 'btn-leave';
}
