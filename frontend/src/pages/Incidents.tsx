import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Incident } from "../types";

function inr(n: number) {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export default function Incidents() {
  const nav = useNavigate();
  const [items, setItems] = useState<Incident[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.incidents().then((r) => setItems(r.items)).catch((e) => setError(String(e)));
  }, []);

  return (
    <div>
      <h1>Incidents</h1>
      <p className="subtitle">Click a row to inspect the agent pipeline, MoneyGuard, policy, and audit trail.</p>
      {error && <p className="error">{error}</p>}
      <div className="card" style={{ marginTop: 16 }}>
        <table>
          <thead>
            <tr>
              <th>Incident ID</th>
              <th>Merchant</th>
              <th>Amount</th>
              <th>Root cause</th>
              <th>Risk</th>
              <th>Action</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr className="clickable" key={i.incident_id} onClick={() => nav(`/incidents/${i.incident_id}`)}>
                <td className="mono">{i.incident_id}</td>
                <td>{i.merchant_id}</td>
                <td>{inr(i.amount)}</td>
                <td>{i.root_cause}</td>
                <td><span className={`pill ${i.risk_level}`}>{i.risk_level}</span></td>
                <td>{i.action}</td>
                <td><span className={`pill ${i.status}`}>{i.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
