import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { PERM, ROLE_DESCRIPTION, ROLE_LABEL, roleLabels } from "../types";

interface SystemStatus {
  application: string; env: string; ad_enabled: boolean;
  database_ok: boolean; customer_count: number; account_count: number; uptime_note: string;
}

export default function Dashboard() {
  const { employee, can } = useAuth();
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    if (can(PERM.SYSTEM_STATUS_READ)) {
      api.get<SystemStatus>("/api/v1/internal/system/status").then(setStatus).catch(() => {});
    }
  }, []);

  return (
    <>
      <h1>Velkommen, {employee?.display_name}</h1>
      <p className="subtle">
        {employee && employee.roles.length > 1 ? "Dine afdelinger" : "Din afdeling"}:{" "}
        {roleLabels(employee?.roles ?? []) || "ingen"}
      </p>

      {employee && employee.roles.length > 0 && (
        <div className="card">
          <h2>Din adgang</h2>
          <ul>
            {employee.roles.map((r) => (
              <li key={r}>
                <strong>{ROLE_LABEL[r] || r}:</strong> {ROLE_DESCRIPTION[r] || ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2>Genveje</h2>
        <div className="quick-links">
          {can(PERM.CUSTOMER_LOOKUP) && <Link className="btn" to="/kunder">Kundesøgning</Link>}
          {can(PERM.LOAN_DECIDE) && <Link className="btn" to="/laan">Lånebehandling</Link>}
          {can(PERM.AUDIT_READ) && <Link className="btn" to="/audit">Auditlog</Link>}
        </div>
        {employee && employee.permissions.length === 0 && (
          <p className="subtle" style={{ marginTop: 12 }}>
            Du er ikke tilknyttet en afdeling (IT og drift, Kundeservice eller Investering).
            Kontakt IT og drift for at blive tilføjet den rette AD-gruppe.
          </p>
        )}
      </div>

      {status && (
        <div className="card">
          <h2>Systemstatus</h2>
          <table>
            <tbody>
              <tr><th>Applikation</th><td>{status.application} ({status.env})</td></tr>
              <tr><th>Database</th><td>{status.database_ok ? "OK" : "Fejl"}</td></tr>
              <tr><th>AD aktiveret</th><td>{status.ad_enabled ? "Ja" : "Nej (testadapter)"}</td></tr>
              <tr><th>Kunder</th><td>{status.customer_count}</td></tr>
              <tr><th>Konti</th><td>{status.account_count}</td></tr>
            </tbody>
          </table>
          <p className="subtle">{status.uptime_note}</p>
        </div>
      )}
    </>
  );
}
