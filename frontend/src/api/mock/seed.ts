/**
 * A plausible evening's service, so the prototype opens on a working door
 * rather than an empty screen — and so the estimator has real turnaround
 * history to blend against its priors from the first click.
 *
 * The backend equivalent of this is `make seed`.
 */
import type { Config } from '../types';
import type { MockState, StoredParty } from './store';
import { newToken } from './token';

interface Closed {
  name: string;
  size: number;
  /** Minutes before now that the party joined the list. */
  joinedAgo: number;
  /** Minutes from joining to being seated. */
  turnaround: number;
  /** What the estimator told them at the door. */
  quoted: number;
}

const SEATED: Closed[] = [
  { name: 'Marsh', size: 2, joinedAgo: 205, turnaround: 22, quoted: 25 },
  { name: 'Ferreira', size: 4, joinedAgo: 198, turnaround: 44, quoted: 40 },
  { name: 'Nakamura', size: 2, joinedAgo: 190, turnaround: 26, quoted: 25 },
  { name: 'Oyelaran', size: 5, joinedAgo: 182, turnaround: 58, quoted: 55 },
  { name: 'Baptiste', size: 3, joinedAgo: 176, turnaround: 38, quoted: 40 },
  { name: 'Kowalczyk', size: 2, joinedAgo: 168, turnaround: 19, quoted: 25 },
  { name: 'Ainsley', size: 4, joinedAgo: 160, turnaround: 51, quoted: 40 },
  { name: 'Rasmussen', size: 7, joinedAgo: 150, turnaround: 78, quoted: 75 },
  { name: 'Delacroix', size: 2, joinedAgo: 141, turnaround: 24, quoted: 25 },
  { name: 'Haddad', size: 6, joinedAgo: 132, turnaround: 61, quoted: 55 },
  { name: 'Strand', size: 4, joinedAgo: 120, turnaround: 35, quoted: 40 },
  { name: 'Iqbal', size: 2, joinedAgo: 108, turnaround: 31, quoted: 25 },
  { name: 'Bellweather', size: 3, joinedAgo: 96, turnaround: 42, quoted: 40 },
  { name: 'Sorrentino', size: 2, joinedAgo: 84, turnaround: 23, quoted: 25 },
  { name: 'Achebe', size: 5, joinedAgo: 70, turnaround: 54, quoted: 55 },
  { name: 'Mendelsohn', size: 4, joinedAgo: 58, turnaround: 46, quoted: 40 },
];

interface Waiting {
  name: string;
  size: number;
  joinedAgo: number;
  /** Minutes before now that the host called them, if they have been called. */
  notifiedAgo?: number;
  phone?: string;
  note?: string;
  quoted: number;
}

const ON_THE_LIST: Waiting[] = [
  { name: 'Dana Whitcomb', size: 4, joinedAgo: 34, note: 'Highchair', quoted: 40 },
  { name: 'Okonjo', size: 2, joinedAgo: 27, notifiedAgo: 4, phone: '555 0147', quoted: 25 },
  { name: 'Vasquez', size: 6, joinedAgo: 22, note: 'Patio if one opens', quoted: 55 },
  { name: 'Lindqvist', size: 2, joinedAgo: 15, quoted: 25 },
  { name: 'Behrouzi', size: 8, joinedAgo: 11, note: 'Birthday, no candles', quoted: 75 },
  { name: 'Dupont', size: 3, joinedAgo: 5, phone: '555 0192', quoted: 40 },
];

export function buildSeed(config: Config): MockState {
  const now = Date.now();
  const at = (minutesAgo: number) => new Date(now - minutesAgo * 60_000).toISOString();

  const parties: StoredParty[] = [];
  let id = 1;

  const base = (name: string, size: number, joinedAgo: number, quoted: number): StoredParty => ({
    id: id++,
    token: newToken(),
    name,
    size,
    phone: null,
    note: null,
    status: 'WAITING',
    quoted_wait_minutes: quoted,
    joined_at: at(joinedAgo),
    notified_at: null,
    seated_at: null,
    closed_at: null,
  });

  for (const entry of SEATED) {
    const party = base(entry.name, entry.size, entry.joinedAgo, entry.quoted);
    const seatedAgo = entry.joinedAgo - entry.turnaround;
    party.status = 'SEATED';
    party.notified_at = at(seatedAgo + 4);
    party.seated_at = at(seatedAgo);
    party.closed_at = at(seatedAgo);
    parties.push(party);
  }

  // One party the host called who never came back, and two that gave up.
  const trelawny = base('Trelawny', 2, 92, 25);
  trelawny.status = 'NO_SHOW';
  trelawny.notified_at = at(68);
  trelawny.closed_at = at(60);
  parties.push(trelawny);

  const kaur = base('Kaur', 4, 78, 40);
  kaur.status = 'CANCELLED';
  kaur.closed_at = at(70);
  kaur.note = 'Went next door';
  parties.push(kaur);

  const novak = base('Novak', 2, 46, 25);
  novak.status = 'CANCELLED';
  novak.notified_at = at(30);
  novak.closed_at = at(26);
  parties.push(novak);

  for (const entry of ON_THE_LIST) {
    const party = base(entry.name, entry.size, entry.joinedAgo, entry.quoted);
    party.phone = entry.phone ?? null;
    party.note = entry.note ?? null;
    if (entry.notifiedAgo !== undefined) {
      party.status = 'NOTIFIED';
      party.notified_at = at(entry.notifiedAgo);
    }
    parties.push(party);
  }

  return { nextId: id, parties, config: structuredClone(config), signedIn: false };
}
