import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import type { AuditEvent, IncidentDetail } from "../types";

const STAGES = [
  { title: "EVENT", match: "revenue" },
  { title: "DETECTION", match: "revenue_detector" },
  { title: "PAYMENT INVESTIGATION", match: "payment_investigator" },
  { title: "CUSTOMER ANALYSIS", match: "customer_agent" },
  { title: "ROOT CAUSE", match: "root_cause" },
  { title: "MONEYGUARD", match: "moneyguard" },
  { title: "POLICY", match: "policy_engine" },
  { title: "ACTION", match: "recovery_simulator" },
  { title: "VERIFICATION", match: "verification" },
];

export default function Investigation() {
  const { id } = useParams();
  const [inc, setInc] = useState<IncidentDetail | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([api.incident(id), api.audit(id)])
      .then(([a, b]) => {
        setInc(a);
        setAudit(b);
      })
      .catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <p className="error">{error}</p>;
  if (!inc) return <p className="subtitle">Loading investigation…</p>;

  return (
    <div>
      <h1>Investigation {inc.incident_id}</h1>
      <p className="mono">trace_id {inc.trace_id}</p>
      <p className="subtitle">
        {inc.root_cause} · {inc.action} · {inc.status} · recovered ₹{inc.revenue_recovered.toLocaleString("en-IN")}
      </p>
      <div className="pipeline" style={{ marginTop: 16 }}>
        {STAGES.map((s) => {
          const agent = inc.agent_results.find((a) => a.agent === s.match) || (s.title === "EVENT" ? inc.agent_results[0] : undefined);
          return (
            <div className="stage" key={s.title}>
              <h3>{s.title}</h3>
              <div className="mono">
                {agent ? `${agent.ok ? "ok" : "fallback"} · ${(agent.confidence * 100).toFixed(0)}%` : "pending"}
              </div>
              <div>{agent?.decision}</div>
              <div className="subtitle">{agent?.explanation}</div>
              {agent?.evidence && (
                <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(agent.evidence, null, 2).slice(0, 800)}
                </pre>
              )}
            </div>
          );
        })}
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2 style={{ fontSize: 16, marginTop: 0 }}>Audit trail</h2>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Agent</th>
              <th>Decision</th>
              <th>Action</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {audit.map((e) => (
              <tr key={e.id}>
                <td className="mono">{e.timestamp}</td>
                <td>{e.event}</td>
                <td>{e.agent}</td>
                <td>{e.decision}</td>
                <td>{e.action}</td>
                <td>{e.result}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
