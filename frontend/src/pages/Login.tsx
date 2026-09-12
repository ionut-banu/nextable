import { useState, type FormEvent } from 'react';
import { DEMO_PASSWORD, login } from '../api/client';
import { errorMessage } from '../api/errors';

export function Login({ onSignedIn }: { onSignedIn: () => void }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(password);
      onSignedIn();
    } catch (caught) {
      setError(errorMessage(caught));
      setPassword('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <form className="login-card" onSubmit={handleSubmit}>
        <div>
          <h1 className="login-mark">Nextable</h1>
          <p className="login-lead">The front door, for whoever is working it.</p>
        </div>

        {error && <p className="notice">{error}</p>}

        <div>
          <label className="field-label" htmlFor="staff-password">
            Staff password
          </label>
          <input
            id="staff-password"
            className="field-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            autoFocus
            required
          />
        </div>

        <button className="btn btn-solid" type="submit" disabled={busy}>
          {busy ? 'Checking' : 'Sign in'}
        </button>

        <p className="login-hint">
          Prototype running on mock data. The password is {DEMO_PASSWORD}.
        </p>
      </form>
    </main>
  );
}
