import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ApiException } from "../api";
import DemoBanner from "../components/DemoBanner";

const BANK = (import.meta.env.VITE_BANK_NAME as string) || "Demobank";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setBusy(true);
    try {
      await login(username.trim(), password);
      navigate("/");
    } catch (err) {
      if (err instanceof ApiException && err.status === 403) {
        setError("Du har ikke adgang til medarbejderportalen.");
      } else if (err instanceof ApiException && err.status === 429) {
        setError("For mange forsøg. Prøv igen senere.");
      } else {
        setError("Forkert brugernavn eller adgangskode.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <DemoBanner />
      <header className="topbar">
        <div className="brand"><span className="logo" />{BANK} · Intern</div>
      </header>
      <div className="auth-wrap">
        <div className="auth-card">
          <div className="card">
            <h1>Medarbejderlogin</h1>
            <p className="subtle">Log ind med din AD-konto (BANK-domænet).</p>
            {error && <div className="alert error">{error}</div>}
            <form onSubmit={onSubmit}>
              <label htmlFor="u">AD-brugernavn</label>
              <input id="u" value={username} autoFocus placeholder="fx ida"
                     onChange={(e) => setUsername(e.target.value)} />
              <label htmlFor="p">Adgangskode</label>
              <input id="p" type="password" value={password}
                     onChange={(e) => setPassword(e.target.value)} />
              <div style={{ marginTop: 18 }}>
                <button type="submit" disabled={busy} style={{ width: "100%" }}>
                  {busy ? "Logger ind…" : "Log ind med AD"}
                </button>
              </div>
            </form>
          </div>
          <p className="muted-center">Adgang og roller styres i Active Directory.</p>
        </div>
      </div>
    </>
  );
}
