import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Account } from "../types";
import { kr, kontotype } from "../util";

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Account[]>("/api/v1/customer/accounts")
      .then(setAccounts).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="subtle">Indlæser…</p>;

  return (
    <>
      <h1>Mine konti</h1>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Kontonummer</th><th>Type</th><th>Status</th>
              <th>Valuta</th><th className="amount">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id}>
                <td><Link to={`/konti/${a.id}`}>{a.account_number}</Link></td>
                <td>{kontotype(a.account_type)}</td>
                <td><span className={"badge " + a.status}>{a.status === "ACTIVE" ? "Aktiv" : a.status === "FROZEN" ? "Spærret" : "Lukket"}</span></td>
                <td>{a.currency}</td>
                <td className="amount">{kr(a.balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
