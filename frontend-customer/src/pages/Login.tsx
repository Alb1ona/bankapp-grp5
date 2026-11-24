import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ApiException } from "../api";
import DemoBanner from "../components/DemoBanner";

const BANK = (import.meta.env.VITE_BANK_NAME as string) || "Demobank";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(identifier.trim(), password);
      navigate("/");
    } catch (err) {
      if (err instanceof ApiException && err.status === 429) {
        setError("For mange forsøg. Vent et øjeblik og prøv igen.");
      } else {
        setError("Forkert login eller adgangskode.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <DemoBanner />
      <header className="topbar">
        <div className="brand"><span className="logo" />{BANK}</div>
      </header>
      <div className="auth-wrap">
        <div className="auth-card">
          <div className="card">
            <h1>Log ind i netbank</h1>
            <p className="subtle">Brug din e-mail eller dit kundenummer.</p>
            {error && <div className="alert error">{error}</div>}
            <form onSubmit={onSubmit}>
              <label htmlFor="identifier">E-mail eller kundenummer</label>
              <input id="identifier" value={identifier} autoFocus
                     onChange={(e) => setIdentifier(e.target.value)} />
              <label htmlFor="password">Adgangskode</label>
              <input id="password" type="password" value={password}
                     onChange={(e) => setPassword(e.target.value)} />
              <div style={{ marginTop: 18 }}>
                <button type="submit" disabled={busy} style={{ width: "100%" }}>
                  {busy ? "Logger ind…" : "Log ind"}
                </button>
              </div>
            </form>
          </div>
          <p className="muted-center">
            Demo: Investeringsrådgivning og rigtige betalinger er ikke en del af systemet.
          </p>
        </div>
      </div>
    </>
  );
}
