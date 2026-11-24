import { useEffect, useMemo, useState } from "react";
import { api, ApiException } from "../api";
import type { Account, Transfer as TransferT } from "../types";
import { kr, kontotype, randomKey } from "../util";

export default function Transfer() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [sender, setSender] = useState("");
  const [receiver, setReceiver] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [step, setStep] = useState<"form" | "confirm" | "done">("form");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TransferT | null>(null);
  // Fast idempotency-nøgle pr. bekræftelses-session (FR-10).
  const [idemKey, setIdemKey] = useState("");

  useEffect(() => {
    api.get<Account[]>("/api/v1/customer/accounts").then((accs) => {
      setAccounts(accs.filter((a) => a.status === "ACTIVE"));
      if (accs.length) setSender(accs[0].id);
    });
  }, []);

  const senderAcc = useMemo(() => accounts.find((a) => a.id === sender), [accounts, sender]);

  function toConfirm(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const amt = parseFloat(amount.replace(",", "."));
    if (!sender) return setError("Vælg en afsenderkonto.");
    if (!receiver.trim()) return setError("Indtast modtagerens kontonummer.");
    if (!(amt > 0)) return setError("Beløbet skal være positivt.");
    if (senderAcc && amt > parseFloat(senderAcc.balance)) {
      return setError("Beløbet overstiger saldoen på afsenderkontoen.");
    }
    setIdemKey(randomKey());
    setStep("confirm");
  }

  async function confirmTransfer() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<TransferT>("/api/v1/customer/transfers", {
        sender_account_id: sender,
        receiver_account_number: receiver.trim(),
        amount: parseFloat(amount.replace(",", ".")).toFixed(2),
        description: description.trim() || null,
        idempotency_key: idemKey,
      });
      setResult(res);
      setStep("done");
    } catch (err) {
      if (err instanceof ApiException) setError(err.message);
      else setError("Overførslen kunne ikke gennemføres.");
      setStep("form");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setReceiver(""); setAmount(""); setDescription("");
    setResult(null); setError(null); setStep("form");
  }

  return (
    <>
      <h1>Overførsel</h1>
      <p className="subtle">Overfør mellem egne konti eller til en anden konto i banken.</p>

      {error && <div className="alert error">{error}</div>}

      {step === "form" && (
        <div className="card" style={{ maxWidth: 520 }}>
          <form onSubmit={toConfirm}>
            <label htmlFor="sender">Fra konto</label>
            <select id="sender" value={sender} onChange={(e) => setSender(e.target.value)}>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {kontotype(a.account_type)} · {a.account_number} ({kr(a.balance)})
                </option>
              ))}
            </select>

            <label htmlFor="receiver">Til kontonummer</label>
            <input id="receiver" value={receiver} placeholder="fx 5001000003"
                   onChange={(e) => setReceiver(e.target.value)} />

            <label htmlFor="amount">Beløb (DKK)</label>
            <input id="amount" inputMode="decimal" value={amount} placeholder="0,00"
                   onChange={(e) => setAmount(e.target.value)} />

            <label htmlFor="desc">Tekst (valgfri)</label>
            <input id="desc" value={description} maxLength={140}
                   onChange={(e) => setDescription(e.target.value)} />

            <div style={{ marginTop: 18 }}>
              <button type="submit">Fortsæt</button>
            </div>
          </form>
        </div>
      )}

      {step === "confirm" && (
        <div className="card" style={{ maxWidth: 520 }}>
          <h2>Bekræft overførsel</h2>
          <table>
            <tbody>
              <tr><th>Fra</th><td>{senderAcc?.account_number}</td></tr>
              <tr><th>Til</th><td>{receiver}</td></tr>
              <tr><th>Beløb</th><td>{kr(parseFloat(amount.replace(",", ".")))}</td></tr>
              <tr><th>Tekst</th><td>{description || "—"}</td></tr>
            </tbody>
          </table>
          <div className="row-between" style={{ marginTop: 16 }}>
            <button className="btn-secondary" onClick={() => setStep("form")} disabled={busy}>
              Tilbage
            </button>
            <button onClick={confirmTransfer} disabled={busy}>
              {busy ? "Gennemfører…" : "Bekræft og overfør"}
            </button>
          </div>
        </div>
      )}

      {step === "done" && result && (
        <div className="card" style={{ maxWidth: 520 }}>
          <div className="alert ok">Overførslen er gennemført.</div>
          <table>
            <tbody>
              <tr><th>Status</th><td><span className={"badge " + result.status}>{result.status}</span></td></tr>
              <tr><th>Beløb</th><td>{kr(result.amount)}</td></tr>
              <tr><th>Reference</th><td>{result.id}</td></tr>
            </tbody>
          </table>
          <div style={{ marginTop: 16 }}>
            <button onClick={reset}>Ny overførsel</button>
          </div>
        </div>
      )}
    </>
  );
}
