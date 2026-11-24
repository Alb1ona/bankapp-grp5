import { useState } from "react";
import { api } from "../api";
import type { AccountAdminView, CustomerSearchResult } from "../types";
import { kr, kontotype } from "../util";

export default function CustomerSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<CustomerSearchResult[]>([]);
  const [selected, setSelected] = useState<CustomerSearchResult | null>(null);
  const [accounts, setAccounts] = useState<AccountAdminView[]>([]);
  const [searched, setSearched] = useState(false);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    const res = await api.get<CustomerSearchResult[]>(
      `/api/v1/internal/customers?q=${encodeURIComponent(q.trim())}`);
    setResults(res);
    setSelected(null);
    setAccounts([]);
    setSearched(true);
  }

  async function openCustomer(c: CustomerSearchResult) {
    setSelected(c);
    const accs = await api.get<AccountAdminView[]>(
      `/api/v1/internal/customers/${c.customer_id}/accounts`);
    setAccounts(accs);
  }

  return (
    <>
      <h1>Kundesøgning</h1>
      <p className="subtle">Skrivebeskyttet opslag. Du kan ikke ændre kundens data her.</p>

      <div className="card">
        <form onSubmit={search} className="row-between">
          <input value={q} placeholder="Navn, kundenummer eller e-mail"
                 onChange={(e) => setQ(e.target.value)} />
          <button type="submit" style={{ marginLeft: 10 }}>Søg</button>
        </form>
      </div>

      {searched && (
        <div className="card">
          <h2>Resultater ({results.length})</h2>
          <table>
            <thead><tr><th>Kundenr.</th><th>Navn</th><th>E-mail</th><th></th></tr></thead>
            <tbody>
              {results.map((c) => (
                <tr key={c.customer_id}>
                  <td>{c.customer_number}</td>
                  <td>{c.full_name}</td>
                  <td>{c.email}</td>
                  <td><button className="btn-secondary" onClick={() => openCustomer(c)}>Vis konti</button></td>
                </tr>
              ))}
              {results.length === 0 && <tr><td colSpan={4} className="subtle">Ingen resultater.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="card">
          <h2>{selected.full_name} · {selected.customer_number}</h2>
          <table>
            <thead><tr><th>Konto</th><th>Type</th><th>Status</th><th className="amount">Saldo</th></tr></thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.id}>
                  <td>{a.account_number}</td>
                  <td>{kontotype(a.account_type)}</td>
                  <td><span className={"badge " + a.status}>{a.status}</span></td>
                  <td className="amount">{kr(a.balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
