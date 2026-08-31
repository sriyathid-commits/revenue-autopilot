import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { AuditEvent, IncidentDetail } from "../types";

function inr(n: number) {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "var(--good)" : pct >= 55 ? "var(--warn)" : "var(--bad)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: "var(--line)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 700, minWidth: 32 }}>{pct}%</span>
    </div>
  );
}

const PIPELINE_STAGES = [
  { agent: "revenue_detector",   label: "Revenue Detector",       icon: "📡", desc: "Detects revenue leakage and at-risk clusters" },
  { agent: "payment_investigator", label: "Payment Investigator", icon: "🔎", desc: "Analyses gateway, method, and failure patterns" },
  { agent: "customer_agent",     label: "Customer Analyst",       icon: "👤", desc: "Evaluates customer intent and recovery probability" },
  { agent: "root_cause",         label: "Root Cause Agent",       icon: "🧠", desc: "Combines evidence into a named root cause" },
  { agent: "moneyguard",         label: "MoneyGuard",             icon: "🛡️", desc: "Safety boundary — evaluates AI proposal" },
  { agent: "policy_engine",      label: "Policy Engine",          icon: "⚖️", desc: "Deterministic authorization of recovery action" },
  { agent: "recovery_simulator", label: "Recovery Simulator",     icon: "⚡", desc: "Test-mode execution — no real money moved" },
  { agent: "verification",       label: "Verification",           icon: "✅", desc: "Confirms outcome and counts recovered revenue" },
];

function StageCard({
  icon,
  label,
  desc,
  agent,
  decision,
  confidence,
  explanation,
  ok,
  isLast,
}: {
  icon: string;
  label: string;
  desc: string;
  agent: string;
  decision: string;
  confidence: number;
  explanation: string;
  ok: boolean;
  isLast: boolean;
}) {
  const isStop = ["STOP", "BLOCKED", "NO_ACTION", "HUMAN_REVIEW"].includes(decision);
  const isGood = ["VERIFIED", "PAYMENT_SUCCESS", "ALTERNATE_PAYMENT", "SAFE_RETRY",
                  "PERSONALIZED_OFFER", "RECOVERY_MESSAGE", "APPROVED"].includes(decision);

  return (
    <div className="trace-stage-wrap">
      <div className={`trace-stage ${isStop ? "trace-stage--stop" : isGood ? "trace-stage--good" : ""}`}>
        <div className="trace-stage-header">
          <span className="trace-stage-icon">{icon}</span>
          <div className="trace-stage-meta">
            <div className="trace-stage-label">{label}</div>
            <div className="trace-stage-desc">{desc}</div>
          </div>
          <span className={`pill ${isStop ? "HIGH" : isGood ? "LOW" : "MEDIUM"}`}>
            {decision || "—"}
          </span>
        </div>
        <div style={{ marginTop: 8 }}>
          <ConfBar value={confidence} />
        </div>
        {explanation && (
          <p className="trace-stage-explanation">{explanation}</p>
        )}
        <div className="trace-stage-agent">
          <span className="mono">{agent}</span>
          {!ok && <span className="pill MEDIUM" style={{ marginLeft: 6 }}>fallback</span>}
        </div>
      </div>
      {!isLast && (
        <div className="trace-connector">
          <span className="trace-arrow">↓</span>
        </div>
      )}
    </div>
  );
}

export default function Investigation() {
  const { id } = useParams();
  const nav = useNavigate();
  const [inc, setInc] = useState<IncidentDetail | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAudit, setShowAudit] = useState(false);

  useEffect(() => {
    if (!id) return;
    Promise.all([api.incident(id), api.audit(id)])
      .then(([a, b]) => { setInc(a); setAudit(b); })
      .catch((e) => setError(String(e)));
  }, [id]);

  if (error) return (
    <div>
      <button className="btn ghost" style={{ marginBottom: 16 }} onClick={() => nav(-1)}>← Back</button>
      <div className="error-box"><strong>Error</strong><p>{error}</p></div>
    </div>
  );

  if (!inc) return (
    <div>
      <button className="btn ghost" style={{ marginBottom: 16 }} onClick={() => nav(-1)}>← Back</button>
      <div className="skeleton-table">
        {[1,2,3,4].map(i => <div className="skeleton-row" key={i}><div className="skeleton-cell" style={{flex:1, height:80}} /></div>)}
      </div>
    </div>
  );

  const recovered = inc.revenue_recovered > 0;
  const isBlocked = ["BLOCKED", "STOP"].includes(inc.status);

  return (
    <div>
      <button className="btn ghost" style={{ marginBottom: 16 }} onClick={() => nav(-1)}>
        ← Back to incidents
      </button>

      {/* Incident summary header */}
      <div className="card trace-header">
        <div className="trace-header-top">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <h1 style={{ margin: 0, fontSize: 18 }}>{inc.incident_id}</h1>
              <span className={`pill ${inc.status}`}>{inc.status}</span>
              <span className={`pill ${inc.risk_level}`}>{inc.risk_level}</span>
            </div>
            <p className="mono" style={{ margin: "4px 0 0", fontSize: 11 }}>trace {inc.trace_id}</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="label">Revenue at risk</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "var(--warn)" }}>{inr(inc.revenue_at_risk)}</div>
            <div className="label" style={{ marginTop: 6 }}>Recovered</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: recovered ? "var(--good)" : "var(--bad)" }}>
              {inr(inc.revenue_recovered)}
            </div>
          </div>
        </div>
        <div className="trace-header-grid">
          <div><span className="label">Merchant</span><br />{inc.merchant_id}</div>
          <div><span className="label">Root cause</span><br />{inc.root_cause ?? "—"}</div>
          <div><span className="label">Action</span><br />{inc.action}</div>
          <div><span className="label">Confidence</span><br />{(inc.confidence * 100).toFixed(0)}%</div>
        </div>

        {/* Story summary */}
        <div className={`trace-story ${recovered ? "trace-story--good" : isBlocked ? "trace-story--bad" : ""}`}>
          {recovered
            ? `✅ AI identified ${inc.root_cause ?? "an issue"}, MoneyGuard approved recovery, Policy authorized, Simulator confirmed — ${inr(inc.revenue_recovered)} recovered in test mode.`
            : isBlocked
            ? `🛡️ MoneyGuard or Policy Engine blocked this action (${inc.root_cause ?? "risk signal"}). No automatic money movement. Zero revenue counted.`
            : `⏳ Incident processed — ${inc.action}. ${inr(inc.revenue_recovered)} recovered.`
          }
        </div>
      </div>

      {/* Decision Trace */}
      <div style={{ marginTop: 20 }}>
        <h2 style={{ fontSize: 15, marginBottom: 14 }}>
          🔗 Decision Trace — full agent pipeline
        </h2>
        <div className="trace-pipeline">
          {PIPELINE_STAGES.map((stage, idx) => {
            const result = inc.agent_results.find((a) => a.agent === stage.agent);
            if (!result) return null;
            return (
              <StageCard
                key={stage.agent}
                icon={stage.icon}
                label={stage.label}
                desc={stage.desc}
                agent={stage.agent}
                decision={result.decision}
                confidence={result.confidence}
                explanation={result.explanation}
                ok={result.ok}
                isLast={idx === PIPELINE_STAGES.length - 1}
              />
            );
          })}
        </div>
      </div>

      {/* Audit trail toggle */}
      <div style={{ marginTop: 20 }}>
        <button
          className="btn ghost"
          onClick={() => setShowAudit((v) => !v)}
        >
          {showAudit ? "▲ Hide" : "▼ Show"} raw audit trail ({audit.length} events)
        </button>

        {showAudit && (
          <div className="card" style={{ marginTop: 10, padding: 0, overflow: "hidden" }}>
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
                    <td className="mono" style={{ fontSize: 10 }}>
                      {new Date(e.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ fontSize: 11 }}>{e.event}</td>
                    <td className="mono" style={{ fontSize: 11 }}>{e.agent}</td>
                    <td style={{ fontSize: 11 }}>{e.decision}</td>
                    <td style={{ fontSize: 11 }}>{e.action ?? "—"}</td>
                    <td className="subtitle" style={{ fontSize: 10 }}>{e.result ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
