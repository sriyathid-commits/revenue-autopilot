import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useRealtime } from "../context/RealtimeContext";
import type { DemoResponse, Incident, Metrics } from "../types";

function inr(n: number) {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export default function Dashboard() {
  const nav = useNavigate();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [demo, setDemo] = useState<DemoResponse | null>(null);
  const [visible, setVisible] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Real-time updates from WebSocket
  const { latestMetrics, latestIncident, connected } = useRealtime();

  // Refresh incident list when a new incident arrives over WebSocket
  const prevIncidentId = useRef<string | null>(null);

  async function load() {
    const [m, i] = await Promise.all([api.metrics(), api.incidents()]);
    setMetrics(m);
    setIncidents(i.items);
  }

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, []);

  // Push live metric updates from WebSocket into state
  useEffect(() => {
    if (latestMetrics) setMetrics(latestMetrics);
  }, [latestMetrics]);

  // Refresh incident list whenever a new incident is broadcast
  useEffect(() => {
    if (!latestIncident) return;
    if (latestIncident.incident_id === prevIncidentId.current) return;
    prevIncidentId.current = latestIncident.incident_id;
    api.incidents()
      .then((r) => setIncidents(r.items))
      .catch(() => undefined);
  }, [latestIncident]);

  async function runDemo() {
    setBusy(true);
    setError(null);
    setVisible(0);
    try {
      await api.demoReset();
      const result = await api.demoRun();
      setDemo(result);
      setMetrics(result.metrics);
      const inc = await api.incidents();
      setIncidents(inc.items);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const steps = useMemo(
    () => demo?.scenarios.flatMap((s) => s.steps.map((st) => ({ ...st, scenario: s.id }))) ?? [],
    [demo],
  );

  useEffect(() => {
    if (!demo || busy) return;
    if (visible >= steps.length) return;
    const t = window.setTimeout(() => setVisible((v) => v + 1), 420);
    return () => window.clearTimeout(t);
  }, [demo, busy, visible, steps.length]);

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Revenue recovery operations</h1>
          <p className="subtitle">
            AI proposes. MoneyGuard evaluates. Policy authorizes. Simulator executes in test mode.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {/* Real-time indicator */}
          <span style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: connected ? "var(--good)" : "var(--bad)",
                display: "inline-block",
                boxShadow: connected ? "0 0 6px var(--good)" : "none",
              }}
            />
            <span style={{ color: "var(--muted)" }}>{connected ? "Live" : "Offline"}</span>
          </span>
          <button className="btn" disabled={busy} onClick={runDemo}>
            {busy ? "Running live demo…" : "Run live demo"}
          </button>
        </div>
      </div>

      <div className="banner">
        This prototype uses synthetic/test-mode financial data and does not move real money.
      </div>
      {error && <p className="error">{error}</p>}

      <div className="kpis">
        <div className="card kpi">
          <div className="label">GMV</div>
          <div className="value">{inr(metrics?.gmv ?? 0)}</div>
        </div>
        <div className="card kpi">
          <div className="label">Transactions</div>
          <div className="value">{(metrics?.transactions ?? 0).toLocaleString()}</div>
        </div>
        <div className="card kpi risk">
          <div className="label">Revenue at risk</div>
          <div className="value">{inr(metrics?.revenue_at_risk ?? 0)}</div>
        </div>
        <div className="card kpi good">
          <div className="label">Revenue recovered</div>
          <div className="value">{inr(metrics?.revenue_recovered ?? 0)}</div>
        </div>
        <div className="card kpi">
          <div className="label">Recovery rate</div>
          <div className="value">{pct(metrics?.recovery_rate ?? 0)}</div>
        </div>
        <div className="card kpi">
          <div className="label">Human reviews</div>
          <div className="value">{metrics?.human_escalations ?? 0}</div>
        </div>
      </div>

      <div className="charts">
        <Chart title="Revenue at risk" data={metrics?.series.revenue_at_risk ?? []} color="#f5c15c" />
        <Chart title="Revenue recovered" data={metrics?.series.revenue_recovered ?? []} color="#3ee0a2" />
        <Chart title="Recovery rate" data={metrics?.series.recovery_rate ?? []} color="#3d8bfd" />
        <Chart title="Payment failure rate" data={metrics?.series.payment_failure_rate ?? []} color="#ff6b7a" />
      </div>

      {demo && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ marginTop: 0, fontSize: 16 }}>Live demo timeline</h2>
          <div className="demo-grid">
            {demo.scenarios.map((s) => (
              <div key={s.id}>
                <strong>
                  {s.id} — {s.name}
                </strong>
                <p className="subtitle">{s.description}</p>
                <p className="mono">trace {s.trace_id}</p>
                <p>
                  At risk {inr(s.revenue_at_risk)} · Recovered {inr(s.revenue_recovered)} · {s.action}
                </p>
                <div className="pipeline">
                  {s.steps.map((st, idx) => {
                    const shownSafe = steps
                      .slice(0, visible)
                      .some((x) => x.title === st.title && x.scenario === s.id);
                    if (!shownSafe && visible <= idx) return null;
                    return (
                      <div className="stage" key={`${s.id}-${idx}`}>
                        <h3>{st.title}</h3>
                        <div className="mono">
                          {st.agent} · conf {(st.confidence * 100).toFixed(0)}%
                        </div>
                        <div>{st.decision}</div>
                        <div className="subtitle">{st.explanation}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0, fontSize: 16 }}>Live incident feed</h2>
        <table>
          <thead>
            <tr>
              <th>Incident</th>
              <th>Merchant</th>
              <th>Amount</th>
              <th>Cause</th>
              <th>Risk</th>
              <th>Action</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {incidents.slice(0, 12).map((i) => (
              <tr
                className="clickable"
                key={i.incident_id}
                onClick={() => nav(`/incidents/${i.incident_id}`)}
              >
                <td className="mono">{i.incident_id}</td>
                <td>{i.merchant_id}</td>
                <td>{inr(i.amount)}</td>
                <td>{i.root_cause}</td>
                <td>
                  <span className={`pill ${i.risk_level}`}>{i.risk_level}</span>
                </td>
                <td>{i.action}</td>
                <td>
                  <span className={`pill ${i.status}`}>{i.status}</span>
                </td>
              </tr>
            ))}
            {incidents.length === 0 && (
              <tr>
                <td colSpan={7} className="subtitle">
                  No incidents yet — stream will populate this automatically, or run the live demo.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Chart({
  title,
  data,
  color,
}: {
  title: string;
  data: { t: string; v: number }[];
  color: string;
}) {
  return (
    <div className="card">
      <p className="chart-title">{title}</p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data}>
          <XAxis dataKey="t" hide />
          <YAxis hide />
          <Tooltip contentStyle={{ background: "#0e1626", border: "1px solid #1e2c48" }} />
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
