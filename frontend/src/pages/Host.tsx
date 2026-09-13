import { useCallback, useEffect, useState } from 'react';
import {
  actOnParty,
  createParty,
  getConfig,
  getStats,
  listParties,
  logout,
  me,
  updateConfig,
} from '../api/client';
import { errorMessage, isApiError } from '../api/errors';
import type { Config, CreatePartyInput, Party } from '../api/types';
import type { PartyAction } from '../lib/transitions';
import { usePoll } from '../hooks/usePoll';
import { useTicker } from '../hooks/useTicker';
import { Login } from './Login';
import { AddPartyForm } from '../components/AddPartyForm';
import { QueueRow } from '../components/QueueRow';
import { GuestLinkSheet } from '../components/GuestLinkSheet';
import { TodayPanel } from '../components/TodayPanel';
import { SettingsPanel } from '../components/SettingsPanel';
import { Toast, type ToastMessage } from '../components/Toast';

type Session = 'unknown' | 'in' | 'out';
type Panel = 'none' | 'today' | 'settings';

const DONE_LABEL: Record<PartyAction, string> = {
  notify: 'notified',
  seat: 'seated',
  'no-show': 'marked as a no-show',
  cancel: 'taken off the list',
};

export default function Host() {
  const [session, setSession] = useState<Session>('unknown');

  useEffect(() => {
    let live = true;
    me()
      .then(() => live && setSession('in'))
      .catch(() => live && setSession('out'));
    return () => {
      live = false;
    };
  }, []);

  if (session === 'unknown') {
    return (
      <main className="login">
        <p className="guest-loading">Opening the console</p>
      </main>
    );
  }

  if (session === 'out') {
    return <Login onSignedIn={() => setSession('in')} />;
  }

  return <Console onSignedOut={() => setSession('out')} />;
}

function Console({ onSignedOut }: { onSignedOut: () => void }) {
  const [panel, setPanel] = useState<Panel>('none');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [linkFor, setLinkFor] = useState<Party | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const now = useTicker(10_000);

  const loadQueue = useCallback(() => listParties('active'), []);
  const queue = usePoll<Party[]>(loadQueue, { intervalMs: 5000 });

  const loadStats = useCallback(() => getStats(), []);
  const stats = usePoll(loadStats, { intervalMs: 5000, enabled: panel === 'today' });

  // The venue name lives in config, and the top rail shows it, so this is not
  // deferred until the settings panel opens.
  useEffect(() => {
    if (config) return;
    let live = true;
    void getConfig()
      .then((loaded) => live && setConfig(loaded))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [config]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function handleFailure(caught: unknown) {
    if (isApiError(caught) && caught.status === 401) {
      onSignedOut();
      return;
    }
    setToast({ text: errorMessage(caught), tone: 'bad' });
  }

  async function handleAdd(input: CreatePartyInput): Promise<boolean> {
    setBusy(true);
    try {
      const party = await createParty(input);
      await queue.refresh();
      setLinkFor(party);
      setToast({ text: `${party.name} added`, tone: 'good' });
      return true;
    } catch (caught) {
      handleFailure(caught);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function handleAction(party: Party, action: PartyAction) {
    setBusy(true);
    try {
      await actOnParty(party.id, action);
      await queue.refresh();
      setToast({ text: `${party.name} ${DONE_LABEL[action]}`, tone: 'good' });
    } catch (caught) {
      // A 409 lands here: another host got there first, or the row is stale.
      handleFailure(caught);
      await queue.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveConfig(next: Config) {
    setBusy(true);
    try {
      const saved = await updateConfig(next);
      setConfig(saved);
      setSavedAt(Date.now());
      await queue.refresh();
      setToast({ text: 'Settings saved', tone: 'good' });
    } catch (caught) {
      handleFailure(caught);
    } finally {
      setBusy(false);
    }
  }


  async function handleSignOut() {
    await logout();
    onSignedOut();
  }

  const parties = queue.data ?? [];
  const guests = parties.reduce((total, party) => total + party.size, 0);

  return (
    <div className="host">
      <header className="host-bar">
        <span className="host-mark">Nextable</span>
        <span className="host-venue">{config?.restaurant_name ?? 'Front door'}</span>
        <nav className="host-bar-actions">
          <button
            type="button"
            className={panel === 'today' ? 'btn btn-quiet host-tab-open' : 'btn btn-quiet'}
            aria-expanded={panel === 'today'}
            onClick={() => setPanel(panel === 'today' ? 'none' : 'today')}
          >
            Today
          </button>
          <button
            type="button"
            className={panel === 'settings' ? 'btn btn-quiet host-tab-open' : 'btn btn-quiet'}
            aria-expanded={panel === 'settings'}
            onClick={() => setPanel(panel === 'settings' ? 'none' : 'settings')}
          >
            Settings
          </button>
          <button type="button" className="btn btn-quiet" onClick={() => void handleSignOut()}>
            Sign out
          </button>
        </nav>
      </header>

      {panel === 'today' && <TodayPanel stats={stats.data} />}
      {panel === 'settings' && config === null && (
        <section className="host-panel">
          <p className="guest-loading">Loading settings</p>
        </section>
      )}
      {panel === 'settings' && config && (
        <SettingsPanel
          config={config}
          saving={busy}
          savedAt={savedAt}
          onSave={(next) => void handleSaveConfig(next)}
        />
      )}

      <main className="host-body">
        <aside className="host-aside">
          <AddPartyForm onAdd={handleAdd} busy={busy} />
        </aside>

        <section className="host-main">
          <div className="queue-head">
            <h1 className="queue-title">Waiting</h1>
            <p className="queue-count">
              <span className="numeral">{parties.length}</span>{' '}
              {parties.length === 1 ? 'party' : 'parties'},{' '}
              <span className="numeral">{guests}</span> {guests === 1 ? 'guest' : 'guests'}
            </p>
          </div>

          {queue.error !== null && <p className="notice">{errorMessage(queue.error)}</p>}

          <ul className="queue">
            {parties.map((party) => (
              <QueueRow
                key={party.id}
                party={party}
                now={now}
                busy={busy}
                onAction={(target, action) => void handleAction(target, action)}
                onShowLink={setLinkFor}
              />
            ))}
            {parties.length === 0 && !queue.loading && (
              <li className="queue-empty">
                <p className="queue-empty-lead">Nobody is waiting.</p>
                <p>Add the first party on the left and hand them their link.</p>
              </li>
            )}
          </ul>
        </section>
      </main>

      {linkFor && <GuestLinkSheet party={linkFor} onClose={() => setLinkFor(null)} />}
      {toast && <Toast message={toast} />}
    </div>
  );
}
