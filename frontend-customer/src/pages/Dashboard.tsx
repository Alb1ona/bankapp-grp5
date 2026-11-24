import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { Account, Transaction } from "../types";
import { kr, dato, kontotype } from "../util";

export default function Dashboard() {
  const { customer } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Account[]>("/api/v1/customer/accounts").then(async (accs) => {
      setAccounts(accs);
      if (accs.length) {
        const tx = await api.get<Transaction[]>(
          `/api/v1/customer/accounts/${accs[0].id}/transactions?limit=5`);
        setRecent(tx);
      }
    }).finally(() => setLoading(false));
  }, []);

  const total = accounts.reduce((s, a) => s + parseFloat(a.balance), 0);

  if (loading) return <p className="subtle">Indlæser…</p>;

  return (
    <>
      <h1>Hej {customer?.first_name}</h1>
      <p className="subtle">Her er et overblik over din økonomi.</p>

      <div className="card">
        <div className="kpi">
          <div className="item">
            <div className="label">Samlet saldo</div>
            <div className="value">{kr(total)}</div>
          </div>
          <div className="item">
            <div className="label">Antal konti</div>
            <div className="value">{accounts.length}</div>
          </div>
        </div>
        <div className="quick-links">
          <Link className="btn" to="/overfoersel">Ny overførsel</Link>
          <Link className="btn btn-secondary" to="/konti">Se konti</Link>
          <Link className="btn btn-secondary" to="/laan">Søg lån</Link>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Dine konti</h2>
          <table>
            <thead><tr><th>Konto</th><th>Type</th><th className="amount">Saldo</th></tr></thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.id}>
                  <td><Link to={`/konti/${a.id}`}>{a.account_number}</Link></td>
                  <td>{kontotype(a.account_type)}</td>
                  <td className="amount">{kr(a.balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h2>Seneste bevægelser</h2>
          {recent.length === 0 && <p className="subtle">Ingen bevægelser endnu.</p>}
          <table>
            <tbody>
              {recent.map((t, i) => (
                <tr key={i}>
                  <td>
                    <div>{t.description || "Postering"}</div>
                    <div className="subtle">{dato(t.created_at)}</div>
                  </td>
                  <td className={"amount " + (parseFloat(t.signed_amount) >= 0 ? "pos" : "neg")}>
                    {kr(t.signed_amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
