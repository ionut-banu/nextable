import type { Stats } from '../api/types';
import { shortDuration } from '../lib/format';

export function TodayPanel({ stats }: { stats: Stats | null }) {
  if (!stats) {
    return (
      <section className="host-panel">
        <p className="guest-loading">Counting up today</p>
      </section>
    );
  }

  const figures: { name: string; value: string | null }[] = [
    { name: 'Parties seated', value: String(stats.parties_seated) },
    { name: 'Guests seated', value: String(stats.guests_seated) },
    { name: 'Average wait', value: minutes(stats.average_wait_minutes) },
    { name: 'Median wait', value: minutes(stats.median_wait_minutes) },
    { name: 'No-shows', value: String(stats.no_show_count) },
    { name: 'Left before seating', value: String(stats.cancelled_count) },
    { name: 'Quotes off by', value: minutes(stats.quote_accuracy_minutes) },
  ];

  return (
    <section className="host-panel">
      <div className="host-panel-head">
        <h2 className="host-panel-title">Today</h2>
        <p className="host-panel-hint">
          Quote accuracy is the gap between what a party was told at the door and how long they
          actually waited.
        </p>
      </div>
      <div className="stat-grid">
        {figures.map((figure) => (
          <div key={figure.name}>
            <p className={figure.value ? 'stat-value' : 'stat-value stat-value-empty'}>
              {figure.value ?? 'Nothing yet'}
            </p>
            <p className="stat-name">{figure.name}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function minutes(value: number | null): string | null {
  return value === null ? null : shortDuration(value);
}
