import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import type { Account, Transaction } from "../types";
import { kr, dato, kontotype } from "../util";

const PAGE = 20;

export default function Transactions() {
  const { accountId } = useParams();
  const [account, setAccount] = useState<Account | null>(null);
  const [tx, setTx] = useState<Transaction[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Account[]>("/api/v1/customer/accounts").then((accs) => {
      setAccount(accs.find((a) => a.id === accountId) || null);
    });
  }, [accountId]);

  useEffect(() => {
    if (!accountId) return;
    setLoading(true);
    api.get<Transaction[]>(
      `/api/v1/customer/accounts/${accountId}/transactions?limit=${PAGE}&offset=${offset}`)
      .then(setTx).finally(() => setLoading(false));
  }, [accountId, offset]);

  return (
    <>
      <div className="row-between">
        <h1>Transaktioner</h1>
        <Link className="btn btn-secondary" to="/konti">Tilbage</Link>
      </div>
      {account && (
        <p className="subtle">
          {kontotype(account.account_type)} · {account.account_number} · Saldo {kr(account.balance)}
        </p>
      )}
      <div className="card">
        {loading ? <p className="subtle">Indlæser…</p> : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Dato</th><th>Beskrivelse</th><th>Modpart</th><th className="amount">Beløb</th>
                </tr>
              </thead>
              <tbody>
                {tx.map((t, i) => (
                  <tr key={i}>
                    <td>{dato(t.created_at)}</td>
                    <td>{t.description || (t.entry_type === "OPENING_BALANCE" ? "Åbningssaldo" : "Postering")}</td>
                    <td>{t.counterpart_account || "—"}</td>
                    <td className={"amount " + (parseFloat(t.signed_amount) >= 0 ? "pos" : "neg")}>
                      {kr(t.signed_amount)}
                    </td>
                  </tr>
                ))}
                {tx.length === 0 && <tr><td colSpan={4} className="subtle">Ingen posteringer.</td></tr>}
              </tbody>
            </table>
            <div className="row-between" style={{ marginTop: 12 }}>
              <button className="btn-secondary" disabled={offset === 0}
                      onClick={() => setOffset(Math.max(0, offset - PAGE))}>Forrige</button>
              <span className="subtle">Side {Math.floor(offset / PAGE) + 1}</span>
              <button className="btn-secondary" disabled={tx.length < PAGE}
                      onClick={() => setOffset(offset + PAGE)}>Næste</button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
