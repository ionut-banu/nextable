import { useState, type FormEvent } from 'react';
import type { CreatePartyInput } from '../api/types';
import { BUCKET_LABELS, bucketForSize } from '../api/mock/estimator';

const QUICK_SIZES = [1, 2, 3, 4, 5, 6, 7, 8];

export function AddPartyForm({
  onAdd,
  busy,
}: {
  onAdd: (input: CreatePartyInput) => Promise<boolean>;
  busy: boolean;
}) {
  const [name, setName] = useState('');
  const [size, setSize] = useState(2);
  const [phone, setPhone] = useState('');
  const [note, setNote] = useState('');

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const added = await onAdd({ name, size, phone, note });
    if (!added) return;
    setName('');
    setSize(2);
    setPhone('');
    setNote('');
  }

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <h2 className="add-title">Add a party</h2>

      <div>
        <label className="field-label" htmlFor="party-name">
          Name
        </label>
        <input
          id="party-name"
          className="field-input"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Whoever the host will call"
          autoComplete="off"
          required
        />
      </div>

      <div>
        <span className="field-label" id="party-size-label">
          People
        </span>
        <div className="add-sizes" role="group" aria-labelledby="party-size-label">
          {QUICK_SIZES.map((value) => (
            <button
              key={value}
              type="button"
              className={value === size ? 'size-chip size-chip-on' : 'size-chip'}
              aria-pressed={value === size}
              onClick={() => setSize(value)}
            >
              {value}
            </button>
          ))}
          <input
            className="field-input bucket-input"
            type="number"
            min={1}
            max={40}
            value={size}
            aria-label="People, if more than eight"
            onChange={(event) => setSize(Math.max(1, Number(event.target.value) || 1))}
          />
        </div>
        <p className="add-bucket-note">{BUCKET_LABELS[bucketForSize(size)]}</p>
      </div>

      <div className="add-pair">
        <div>
          <label className="field-label" htmlFor="party-phone">
            Phone
          </label>
          <input
            id="party-phone"
            className="field-input"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            placeholder="Optional"
            autoComplete="off"
            inputMode="tel"
          />
        </div>
        <div>
          <label className="field-label" htmlFor="party-note">
            Note
          </label>
          <input
            id="party-note"
            className="field-input"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Highchair, patio"
            autoComplete="off"
          />
        </div>
      </div>

      <p className="add-bucket-note">
        The phone number is for your own reference. Nextable never sends messages.
      </p>

      <button className="btn btn-solid" type="submit" disabled={busy}>
        {busy ? 'Adding' : 'Add to waitlist'}
      </button>
    </form>
  );
}
