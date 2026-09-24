import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { ApiError, LOCKED_EVENT, auth, clearAccess, readAccess, type SessionUser } from "../api/client";
import { SessionContext } from "../state/SessionContext";

export function Gate({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const onLocked = () => { setUser(null); setChecking(false); setError(null); };
    window.addEventListener(LOCKED_EVENT, onLocked);
    return () => window.removeEventListener(LOCKED_EVENT, onLocked);
  }, []);
  useEffect(() => {
    const ac = new AbortController();
    if (!readAccess()) { clearAccess(); setChecking(false); return; }
    setChecking(true);
    setError(null);
    auth.me(ac.signal).then(u => { if (!ac.signal.aborted) { setUser(u); setChecking(false); } })
      .catch(e => {
        if (ac.signal.aborted) return;
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) clearAccess();
        else setError("We could not reconnect. Check your connection and try again.");
        setChecking(false);
      });
    return () => ac.abort();
  }, [attempt]);
  useEffect(() => {
    if (!user) return;
    const remaining = Date.parse(readAccess()?.expiresAt ?? "") - Date.now();
    const timer = window.setTimeout(() => { clearAccess(); setUser(null); }, Math.max(0, remaining));
    return () => window.clearTimeout(timer);
  }, [user]);
  if (user) return <SessionContext.Provider value={user}>{children}</SessionContext.Provider>;
  return <main className="login-screen">
    <header className="login-brand"><img src="/ntt-logo.png" alt="NTT DATA" width="110" /><span>Deal Intelligence</span></header>
    <section className="login-card" aria-labelledby="login-title">
      <span className="login-eyebrow">NTT DATA &middot; NORTH AMERICA</span>
      <h1 id="login-title">Sign in to<br />Deal Intelligence.</h1>
      <p className="login-intro">Your deals. Your team. Your next decision.</p>
      {checking ? <p role="status" className="login-status">Restoring your session...</p> : error ?
        <div><p role="alert" className="login-error">{error}</p><button className="login-submit" onClick={() => setAttempt(n => n + 1)}>Try again</button><button className="login-secondary" onClick={() => { clearAccess(); setError(null); }}>Use another account</button></div> :
        <LoginForm onEnter={setUser} />}
    </section>
    <footer className="login-footer">NTT DATA <span>&bull;</span> Sales intelligence, with a clear next step.</footer>
  </main>;
}

function LoginForm({ onEnter }: { onEnter: (user: SessionUser) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inflight = useRef<AbortController | null>(null);
  useEffect(() => () => inflight.current?.abort(), []);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setError(null);
    const ac = new AbortController(); inflight.current = ac;
    try {
      const result = await auth.login(email, password, ac.signal);
      if (!ac.signal.aborted) onEnter(result.user);
    } catch (e) {
      if (ac.signal.aborted) return;
      setError(e instanceof ApiError && e.status === 401 ? "Email or password is incorrect. Please try again." :
        e instanceof ApiError && e.status === 503 ? "Sign-in is not configured yet. Contact your demo administrator." :
        "We could not reach the server. Please try again.");
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="login-form" aria-busy={busy}>
    <label htmlFor="login-email">Email address</label>
    <input id="login-email" name="email" type="email" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={254}
      placeholder="Enter your email address" value={email} readOnly={busy} aria-invalid={!!error} aria-describedby={error ? "login-error" : undefined}
      onChange={e => { setEmail(e.target.value); setError(null); }} />
    <label htmlFor="login-password">Password</label>
    <div className="login-password">
      <input id="login-password" name="password" type={reveal ? "text" : "password"} autoComplete="current-password" required maxLength={256}
        placeholder="Enter your password" value={password} readOnly={busy} aria-invalid={!!error} aria-describedby={error ? "login-error" : undefined}
        onChange={e => { setPassword(e.target.value); setError(null); }} />
      <button type="button" onClick={() => setReveal(v => !v)} aria-label={reveal ? "Hide password" : "Show password"} aria-pressed={reveal}>{reveal ? "Hide" : "Show"}</button>
    </div>
    <div id="login-error" className="login-error" role="alert">{error}</div>
    <button type="submit" className="login-submit" disabled={busy}>{busy ? "Signing in..." : "Sign in"}<span aria-hidden="true">&rarr;</span></button>
    <p className="login-help">Use the account provided for your walkthrough.<br />Your workspace opens based on your assigned role.</p>
  </form>;
}
