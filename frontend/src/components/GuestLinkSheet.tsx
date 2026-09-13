import { useEffect, useRef, useState } from 'react';
import { toDataURL } from 'qrcode';
import type { Party } from '../api/types';
import { guestUrl } from '../lib/format';
import { BUCKET_LABELS } from '../lib/buckets';

/**
 * Shown the moment a party is added, so the host can hand the link over at the
 * door — and reachable again from any row.
 */
export function GuestLinkSheet({ party, onClose }: { party: Party; onClose: () => void }) {
  const [qr, setQr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const url = guestUrl(party.token);

  useEffect(() => {
    let live = true;
    void toDataURL(url, {
      margin: 1,
      width: 512,
      color: { dark: '#101a18', light: '#e8e2d4' },
    }).then((data) => {
      if (live) setQr(data);
    });
    return () => {
      live = false;
    };
  }, [url]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="sheet" onClick={onClose}>
      <div
        className="sheet-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sheet-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="sheet-title" id="sheet-title">
          {party.name} is on the list
        </h2>
        <p className="sheet-lead">
          {BUCKET_LABELS[party.bucket].toLowerCase().replace('tables', 'In the line for tables')},
          {' '}
          {party.quoted_wait_minutes === 0
            ? 'and we can seat them now.'
            : `quoted about ${party.quoted_wait_minutes} minutes.`}
        </p>
        <p className="sheet-lead">
          Let them scan this. It shows their place in line and turns bright when their table is
          ready.
        </p>

        <div className="sheet-qr">
          {qr ? (
            <img src={qr} alt={`Waitlist link for ${party.name}`} />
          ) : (
            <span className="guest-loading">Drawing the code</span>
          )}
        </div>

        <p className="sheet-link">{url}</p>

        <div className="sheet-actions">
          <button className="btn btn-solid" type="button" onClick={() => void copy()}>
            {copied ? 'Copied' : 'Copy link'}
          </button>
          <a className="btn" href={`/w/${party.token}`} target="_blank" rel="noreferrer">
            Open guest view
          </a>
          <button className="btn btn-quiet" type="button" onClick={onClose} ref={closeRef}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
