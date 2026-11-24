import { useEffect, useState } from "react";
import { api, ApiException } from "../api";
import type { LoanAdminView } from "../types";
import { kr, dato } from "../util";

export default function LoanProcessing() {
  const [loans, setLoans] = useState<LoanAdminView[]>([]);
  const [filter, setFilter] = useState("AFVENTER");
  const [active, setActive] = useState<LoanAdminView | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function load() {
    const qs = filter ? `?status=${filter}` : "";
    api.get<LoanAdminView[]>(`/api/v1/internal/loans${qs}`).then(setLoans);
  }
  useEffect(load, [filter]);

  async function decide(approve: boolean) {
    if (!active) return;
    if (note.trim().length < 3) { setError("En begrundelse er obligatorisk."); return; }
    setBusy(true); setError(null);
    try {
      await api.patch(`/api/v1/internal/loans/${active.id}/decision`,
        { approve, decision_note: note.trim() });
      setActive(null); setNote(""); load();
    } catch (err) {
      setError(err instanceof ApiException ? err.message : "Kunne ikke gemme afgørelsen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Lånebehandling</h1>
      <div className="card">
        <label htmlFor="f">Vis</label>
        <select id="f" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 220 }}>
          <option value="AFVENTER">Afventer</option>
          <option value="GODKENDT">Godkendt</option>
          <option value="AFVIST">Afvist</option>
          <option value="">Alle</option>
        </select>
      </div>

      <div className="card">
        <table>
          <thead><tr><th>Dato</th><th>Type</th><th className="amount">Beløb</th><th>Løbetid</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {loans.map((l) => (
              <tr key={l.id}>
                <td>{dato(l.created_at)}</td>
                <td>{l.loan_type}</td>
                <td className="amount">{kr(l.amount)}</td>
                <td>{l.duration_months} mdr.</td>
                <td><span className={"badge " + l.status}>{l.status}</span></td>
                <td>
                  {l.status === "AFVENTER"
                    ? <button className="btn-secondary" onClick={() => { setActive(l); setNote(""); setError(null); }}>Behandl</button>
                    : <span className="subtle">Afgjort</span>}
                </td>
              </tr>
            ))}
            {loans.length === 0 && <tr><td colSpan={6} className="subtle">Ingen ansøgninger.</td></tr>}
          </tbody>
        </table>
      </div>

      {active && (
        <div className="card">
          <h2>Behandl ansøgning</h2>
          <table>
            <tbody>
              <tr><th>Beløb</th><td>{kr(active.amount)}</td></tr>
              <tr><th>Type</th><td>{active.loan_type}</td></tr>
              <tr><th>Løbetid</th><td>{active.duration_months} måneder</td></tr>
              <tr><th>Formål</th><td>{active.purpose}</td></tr>
            </tbody>
          </table>
          {error && <div className="alert error">{error}</div>}
          <label htmlFor="note">Intern begrundelse (obligatorisk)</label>
          <textarea id="note" rows={3} value={note} maxLength={500}
                    onChange={(e) => setNote(e.target.value)} />
          <div className="row-between" style={{ marginTop: 14 }}>
            <button className="btn-secondary" onClick={() => setActive(null)} disabled={busy}>Annullér</button>
            <div style={{ display: "flex", gap: 10 }}>
              <button onClick={() => decide(false)} disabled={busy}
                      style={{ background: "#b91c1c" }}>Afvis</button>
              <button onClick={() => decide(true)} disabled={busy}>Godkend</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
