import { useEffect, useState } from "react";
import { api } from "../api";
import type { Evaluation } from "../types";

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export default function EvaluationPage() {
  const [ev, setEv] = useState<Evaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.evaluation().then(setEv).catch((e) => setError(String(e)));
  }, []);

  return (
    <div>
      <h1>Evaluation</h1>
      <p className="subtitle">Computed from synthetic ground truth. Never hard-coded.</p>
      {error && <p className="error">{error}</p>}
      {ev?.note && <p className="subtitle">{ev.note}</p>}
      <div className="kpis" style={{ marginTop: 16 }}>
        <Metric label="Detection precision" value={pct(ev?.detection_precision ?? 0)} />
        <Metric label="Detection recall" value={pct(ev?.detection_recall ?? 0)} />
        <Metric label="Root cause accuracy" value={pct(ev?.root_cause_accuracy ?? 0)} />
        <Metric label="Recovery success" value={pct(ev?.recovery_success_rate ?? 0)} />
        <Metric label="False intervention" value={pct(ev?.false_intervention_rate ?? 0)} />
        <Metric label="Human escalation" value={pct(ev?.human_escalation_rate ?? 0)} />
      </div>
      <div className="card">
        <p>Revenue at risk detected: ₹{(ev?.revenue_at_risk_detected ?? 0).toLocaleString("en-IN")}</p>
        <p>Ground-truth revenue at risk: ₹{(ev?.ground_truth_revenue_at_risk ?? 0).toLocaleString("en-IN")}</p>
        <p>Revenue recovered (verified): ₹{(ev?.revenue_recovered ?? 0).toLocaleString("en-IN")}</p>
        <p className="subtitle">
          Transactions evaluated: {ev?.transactions_evaluated ?? 0} · Incidents: {ev?.incidents_evaluated ?? 0}
        </p>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}
