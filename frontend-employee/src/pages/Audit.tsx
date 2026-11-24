import { useEffect, useState } from "react";
import { api } from "../api";
import type { AuditEventView } from "../types";
import { dato } from "../util";

export default function Audit() {
  const [events, setEvents] = useState<AuditEventView[]>([]);
  const [eventType, setEventType] = useState("");
  const [result, setResult] = useState("");
  const [requestId, setRequestId] = useState("");

  function load() {
    const p = new URLSearchParams();
    if (eventType) p.set("event_type", eventType);
    if (result) p.set("result", result);
    if (requestId) p.set("request_id", requestId.trim());
    api.get<AuditEventView[]>(`/api/v1/internal/audit/events?${p.toString()}`).then(setEvents);
  }
  useEffect(load, []);

  function sevClass(s: string) {
    return s === "ERROR" ? "neg" : s === "WARNING" ? "" : "pos";
  }

  return (
    <>
      <h1>Auditlog</h1>
      <p className="subtle">Skrivebeskyttet. Hændelser kan ikke ændres eller slettes.</p>

      <div className="card">
        <div className="grid cols-2">
          <div>
            <label htmlFor="et">Hændelsestype</label>
            <input id="et" value={eventType} placeholder="fx TRANSFER_SUCCESS"
                   onChange={(e) => setEventType(e.target.value)} />
          </div>
          <div>
            <label htmlFor="res">Resultat</label>
            <select id="res" value={result} onChange={(e) => setResult(e.target.value)}>
              <option value="">Alle</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="DENIED">DENIED</option>
              <option value="FAILURE">FAILURE</option>
            </select>
          </div>
        </div>
        <label htmlFor="rid">Request-id</label>
        <input id="rid" value={requestId} onChange={(e) => setRequestId(e.target.value)} />
        <div style={{ marginTop: 14 }}><button onClick={load}>Filtrér</button></div>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Tidspunkt</th><th>Hændelse</th><th>Aktør</th>
              <th>Resultat</th><th>Kilde-IP</th><th>Request-id</th><th>Årsag</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{dato(e.timestamp)}</td>
                <td>{e.event_type}</td>
                <td>{e.actor_type || "—"}{e.actor_id ? ` (${e.actor_id.slice(0, 8)}…)` : ""}</td>
                <td className={sevClass(e.severity)}>{e.result}</td>
                <td>{e.source_ip || "—"}</td>
                <td className="subtle">{e.request_id || "—"}</td>
                <td>{e.reason || "—"}</td>
              </tr>
            ))}
            {events.length === 0 && <tr><td colSpan={7} className="subtle">Ingen hændelser.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
