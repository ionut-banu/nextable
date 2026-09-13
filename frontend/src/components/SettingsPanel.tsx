import { useEffect, useState, type FormEvent } from 'react';
import type { Config, SizeBucket } from '../api/types';
import { BUCKET_LABELS, BUCKET_ORDER } from '../lib/buckets';

export function SettingsPanel({
  config,
  saving,
  savedAt,
  onSave,
}: {
  config: Config;
  saving: boolean;
  savedAt: number | null;
  onSave: (config: Config) => void;
}) {
  const [draft, setDraft] = useState<Config>(config);

  useEffect(() => {
    setDraft(config);
  }, [config]);

  function setBucket(bucket: SizeBucket, field: 'default_turn_minutes' | 'table_count', value: number) {
    setDraft((current) => ({
      ...current,
      buckets: {
        ...current.buckets,
        [bucket]: { ...current.buckets[bucket], [field]: value },
      },
    }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSave(draft);
  }

  return (
    <section className="host-panel">
      <div className="host-panel-head">
        <h2 className="host-panel-title">Settings</h2>
        <p className="host-panel-hint">
          Quotes start from these numbers and move toward what your floor actually does, so a
          change here shows up straight away and fades as the night fills in real turnarounds.
        </p>
      </div>

      <form className="settings-form" onSubmit={handleSubmit}>
        <table className="bucket-table">
          <thead>
            <tr>
              <th scope="col">Line</th>
              <th scope="col">Typical turn</th>
              <th scope="col">Tables in play</th>
            </tr>
          </thead>
          <tbody>
            {BUCKET_ORDER.map((bucket) => (
              <tr key={bucket}>
                <td className="bucket-name">{BUCKET_LABELS[bucket]}</td>
                <td>
                  <input
                    className="field-input bucket-input"
                    type="number"
                    min={5}
                    max={240}
                    aria-label={`Typical turn in minutes, ${BUCKET_LABELS[bucket]}`}
                    value={draft.buckets[bucket].default_turn_minutes}
                    onChange={(event) =>
                      setBucket(bucket, 'default_turn_minutes', Number(event.target.value) || 0)
                    }
                  />
                </td>
                <td>
                  <input
                    className="field-input bucket-input"
                    type="number"
                    min={1}
                    max={60}
                    aria-label={`Tables in play, ${BUCKET_LABELS[bucket]}`}
                    value={draft.buckets[bucket].table_count}
                    onChange={(event) =>
                      setBucket(bucket, 'table_count', Number(event.target.value) || 1)
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="settings-row">
          <div>
            <label className="field-label" htmlFor="restaurant-name">
              Name guests see
            </label>
            <input
              id="restaurant-name"
              className="field-input"
              value={draft.restaurant_name}
              onChange={(event) =>
                setDraft((current) => ({ ...current, restaurant_name: event.target.value }))
              }
            />
          </div>
          <div>
            <label className="field-label" htmlFor="history-window">
              Turnarounds remembered
            </label>
            <input
              id="history-window"
              className="field-input"
              type="number"
              min={1}
              max={200}
              value={draft.history_window}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  history_window: Number(event.target.value) || 1,
                }))
              }
            />
          </div>
          <div>
            <label className="field-label" htmlFor="smoothing">
              Weight on the typical turn
            </label>
            <input
              id="smoothing"
              className="field-input"
              type="number"
              min={0}
              max={100}
              value={draft.smoothing_constant}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  smoothing_constant: Number(event.target.value) || 0,
                }))
              }
            />
          </div>
        </div>

        <div className="settings-actions">
          <button className="btn btn-solid" type="submit" disabled={saving}>
            {saving ? 'Saving' : 'Save settings'}
          </button>
          {savedAt !== null && <span className="settings-saved">Saved</span>}
        </div>
      </form>
    </section>
  );
}
