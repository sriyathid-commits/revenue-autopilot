import { useEffect, useState } from "react";
import { api } from "../api";
import type { Evaluation } from "../types";

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function inr(n: number) {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

type BarProps = {
  label: string;
  value: number;      // 0–1
  good?: boolean;     // green bar
  bad?: boolean;      // red bar — lower is better
  subtitle?: string;
};

function MetricBar({ label, value, good, bad, subtitle }: BarProps) {
  const pctVal = Math.round(value * 100);
  const color = bad
    ? value > 0.1
      ? "var(--bad)"
      : "var(--good)"
    : good || value >= 0.7
    ? "var(--good)"
    : value >= 0.4
    ? "var(--warn)"
    : "var(--bad)";

  return (
    <div className="eval-bar-row">
      <div className="eval-bar-header">
        <span className="eval-bar-label">{label}</span>
        <span className="eval-bar-value" style={{ color }}>{pct(value)}</span>
      </div>
      {subtitle && <div className="eval-bar-sub">{subtitle}</div>}
      <div className="eval-bar-track">
        <div
          className="eval-bar-fill"
          style={{ width: `${pctVal}%`, background: color }}
        />
      </div>
    </div>
  );
}

export default function EvaluationPage() {
  const [ev, setEv] = useState<Evaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.evaluation()
      .then(setEv)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Evaluation</h1>
          <p className="subtitle">
            Computed against synthetic ground truth. Never hard-coded.
          </p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {loading && (
        <div className="skeleton-table" style={{ marginTop: 16 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="skeleton-row" key={i} style={{ height: 56 }}>
              <div className="skeleton-cell" style={{ flex: 1 }} />
            </div>
          ))}
        </div>
      )}

      {ev?.note && (
        <div className="banner" style={{ marginTop: 16 }}>
          {ev.note}
        </div>
      )}

      {ev && !loading && (
        <>
          {/* Detection quality */}
          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="eval-section-title">Detection quality</h2>
            <MetricBar
              label="Detection precision"
              value={ev.detection_precision}
              good
              subtitle="Of flagged transactions, how many were true anomalies"
            />
            <MetricBar
              label="Detection recall"
              value={ev.detection_recall}
              good
              subtitle="Of all true anomalies, how many were caught"
            />
            <MetricBar
              label="Root cause accuracy"
              value={ev.root_cause_accuracy}
              good
              subtitle="Correct root cause diagnosis vs ground truth labels"
            />
          </div>

          {/* Recovery quality */}
          <div className="card" style={{ marginTop: 12 }}>
            <h2 className="eval-section-title">Recovery quality</h2>
            <MetricBar
              label="Recovery success rate"
              value={ev.recovery_success_rate}
              good
              subtitle="Approved actions that resulted in verified recovery"
            />
            <MetricBar
              label="False intervention rate"
              value={ev.false_intervention_rate}
              bad
              subtitle="Recovery executed on transactions that shouldn't have been recovered — lower is better"
            />
            <MetricBar
              label="Human escalation rate"
              value={ev.human_escalation_rate}
              subtitle="Incidents routed to human review by MoneyGuard or policy"
            />
          </div>

          {/* Revenue impact */}
          <div className="card" style={{ marginTop: 12 }}>
            <h2 className="eval-section-title">Revenue impact</h2>
            <div className="eval-impact-grid">
              <div className="eval-impact-cell">
                <div className="label">Revenue at risk detected</div>
                <div className="value" style={{ color: "var(--warn)" }}>
                  {inr(ev.revenue_at_risk_detected)}
                </div>
              </div>
              <div className="eval-impact-cell">
                <div className="label">Ground-truth at risk</div>
                <div className="value">{inr(ev.ground_truth_revenue_at_risk)}</div>
              </div>
              <div className="eval-impact-cell">
                <div className="label">Revenue recovered</div>
                <div className="value" style={{ color: "var(--good)" }}>
                  {inr(ev.revenue_recovered)}
                </div>
              </div>
            </div>
          </div>

          {/* Counts */}
          <div className="card" style={{ marginTop: 12 }}>
            <h2 className="eval-section-title">Dataset</h2>
            <div className="eval-impact-grid">
              <div className="eval-impact-cell">
                <div className="label">Transactions evaluated</div>
                <div className="value">{ev.transactions_evaluated.toLocaleString()}</div>
              </div>
              <div className="eval-impact-cell">
                <div className="label">Incidents evaluated</div>
                <div className="value">{ev.incidents_evaluated.toLocaleString()}</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
