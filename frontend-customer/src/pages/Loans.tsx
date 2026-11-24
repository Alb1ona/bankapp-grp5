import { useEffect, useState } from "react";
import { api, ApiException } from "../api";
import type { Loan } from "../types";
import { kr, dato } from "../util";

const TYPES = [
  { v: "FORBRUG", t: "Forbrugslån" },
  { v: "BOLIG", t: "Boliglån" },
  { v: "BIL", t: "Billån" },
  { v: "ANDET", t: "Andet" },
];

function statusText(s: string) {
  return s === "AFVENTER" ? "Afventer" : s === "GODKENDT" ? "Godkendt" : "Afvist";
}

export default function Loans() {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [amount, setAmount] = useState("");
  const [loanType, setLoanType] = useState("FORBRUG");
  const [duration, setDuration] = useState("12");
  const [purpose, setPurpose] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);

  function load() {
    api.get<Loan[]>("/api/v1/customer/loans").then(setLoans);
  }
  useEffect(load, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setOk(false); setBusy(true);
    try {
      await api.post<Loan>("/api/v1/customer/loans", {
        amount: parseFloat(amount.replace(",", ".")).toFixed(2),
        loan_type: loanType,
        duration_months: parseInt(duration, 10),
        purpose: purpose.trim(),
      });
      setOk(true);
      setAmount(""); setPurpose("");
      load();
    } catch (err) {
      setError(err instanceof ApiException ? err.message : "Ansøgningen kunne ikke sendes.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Lån</h1>
      <p className="subtle">Ansøg om lån. En ansøgning udløser ingen automatisk udbetaling.</p>

      <div className="grid cols-2">
        <div className="card">
          <h2>Ny ansøgning</h2>
          {error && <div className="alert error">{error}</div>}
          {ok && <div className="alert ok">Din ansøgning er modtaget og afventer behandling.</div>}
          <form onSubmit={submit}>
            <label htmlFor="type">Lånetype</label>
            <select id="type" value={loanType} onChange={(e) => setLoanType(e.target.value)}>
              {TYPES.map((t) => <option key={t.v} value={t.v}>{t.t}</option>)}
            </select>
            <label htmlFor="amount">Beløb (DKK)</label>
            <input id="amount" inputMode="decimal" value={amount}
                   onChange={(e) => setAmount(e.target.value)} />
            <label htmlFor="dur">Løbetid (måneder)</label>
            <input id="dur" type="number" min={1} max={480} value={duration}
                   onChange={(e) => setDuration(e.target.value)} />
            <label htmlFor="purpose">Formål</label>
            <textarea id="purpose" rows={3} value={purpose} maxLength={300}
                      onChange={(e) => setPurpose(e.target.value)} />
            <div style={{ marginTop: 16 }}>
              <button type="submit" disabled={busy}>{busy ? "Sender…" : "Send ansøgning"}</button>
            </div>
          </form>
        </div>

        <div className="card">
          <h2>Mine ansøgninger</h2>
          {loans.length === 0 && <p className="subtle">Du har ingen ansøgninger endnu.</p>}
          <table>
            <thead><tr><th>Dato</th><th>Type</th><th className="amount">Beløb</th><th>Status</th></tr></thead>
            <tbody>
              {loans.map((l) => (
                <tr key={l.id}>
                  <td>{dato(l.created_at)}</td>
                  <td>{l.loan_type}</td>
                  <td className="amount">{kr(l.amount)}</td>
                  <td><span className={"badge " + l.status}>{statusText(l.status)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
