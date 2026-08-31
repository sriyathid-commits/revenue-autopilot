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

const DEMO_STEPS = [
  "Analysing synthetic transactions…",
  "Detecting payment failures and revenue leakage…",
  "Running multi-agent AI pipeline…",
  "MoneyGuard evaluating recovery proposals…",
  "Applying policy engine decisions…",
  "Executing simulated recoveries…",
  "Verifying outcomes and updating metrics…",
  "Recovery complete ✓",
];

function KpiSkeleton() {
  return (
    <div className="kpis">
      {Array.from({ length: 6 }).map((_, i) => (
        <div className="card kpi" key={i}>
          <div className="skeleton-line short" />
          <div className="skeleton-line tall" style={{ marginTop: 10 }} />
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const nav = useNavigate();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [demo, setDemo] = useState<DemoResponse | null>(null);
  const [visible, setVisible] = useState(0);
  const [busy, setBusy] = useState(false);
  const [demoStep, setDemoStep] = useState(0);
  const [initialLoad, setInitialLoad] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { latestMetrics, latestIncident, connected } = useRealtime();
  const prevIncidentId = useRef<string | null>(null);
  const demoStepTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  async function load() {
    const [m, i] = await Promise.all([api.metrics(), api.incidents()]);
    setMetrics(m);
    setIncidents(i.items);
  }

  useEffect(() => {
    load()
      .catch((e) => setError(String(e)))
      .finally(() => setInitialLoad(false));
  }, []);

  useEffect(() => {
    if (latestMetrics) setMetrics(latestMetrics);
  }, [latestMetrics]);

  useEffect(() => {
    if (!latestIncident) return;
    if (latestIncident.incident_id === prevIncidentId.current) return;
    prevIncidentId.current = latestIncident.incident_id;
    api.incidents().then((r) => setIncidents(r.items)).catch(() => undefined);
  }, [latestIncident]);

  async function runDemo() {
    setBusy(true);
    setError(null);
    setVisible(0);
    setDemoStep(0);

    // Animate progress steps while backend works
    let step = 0;
    demoStepTimer.current = setInterval(() => {
      step += 1;
      if (step < DEMO_STEPS.length - 1) setDemoStep(step);
    }, 1200);

    try {
      await api.demoReset();
      const result = await api.demoRun();
      setDemoStep(DEMO_STEPS.length - 1);
      setDemo(result);
      setMetrics(result.metrics);
      const inc = await api.incidents();
      setIncidents(inc.items);
    } catch (e) {
      setError(
        e instanceof Error && e.message
          ? e.message
          : "Unable to connect to the recovery service. Check that the API server is running.",
      );
    } finally {
      if (demoStepTimer.current) clearInterval(demoStepTimer.current);
      setBusy(false);
    }
  }

  const steps = useMemo(
    () =>
      demo?.scenarios.flatMap((s) =>
        s.steps.map((st) => ({ ...st, scenario: s.id })),
      ) ?? [],
    [demo],
  );

  useEffect(() => {
    if (!demo || busy) return;
    if (visible >= steps.length) return;
    const t = window.setTimeout(() => setVisible((v) => v + 1), 380);
    return () => window.clearTimeout(t);
  }, [demo, busy, visible, steps.length]);

  // Build chart data from series OR seed from demo metrics when series is empty
  function chartData(
    key: keyof Metrics["series"],
    fallback?: { t: string; v: number }[],
  ) {
    const d = metrics?.series[key] ?? [];
    if (d.length > 0) return d;
    return fallback ?? [];
  }

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
            {busy ? "Running…" : "Run live demo"}
          </button>
        </div>
      </div>

      <div className="banner">
        This prototype uses synthetic/test-mode financial data and does not move real money.
      </div>

      {/* Demo progress indicator */}
      {busy && (
        <div className="demo-progress">
          <div className="demo-progress-bar">
            <div
              className="demo-progress-fill"
              style={{
                width: `${Math.round(((demoStep + 1) / DEMO_STEPS.length) * 100)}%`,
              }}
            />
          </div>
          <p className="demo-progress-label">{DEMO_STEPS[demoStep]}</p>
        </div>
      )}

      {error && (
        <div className="error-box">
          <strong>Error</strong>
          <p>{error}</p>
        </div>
      )}

      {initialLoad ? (
        <KpiSkeleton />
      ) : (
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
      )}

      <div className="charts">
        <Chart title="Revenue at risk" data={chartData("revenue_at_risk")} color="#f5c15c" empty={!metrics?.series.revenue_at_risk.length} />
        <Chart title="Revenue recovered" data={chartData("revenue_recovered")} color="#3ee0a2" empty={!metrics?.series.revenue_recovered.length} />
        <Chart title="Recovery rate" data={chartData("recovery_rate")} color="#3d8bfd" empty={!metrics?.series.recovery_rate.length} />
        <Chart title="Payment failure rate" data={chartData("payment_failure_rate")} color="#ff6b7a" empty={!metrics?.series.payment_failure_rate.length} />
      </div>

      {/* Live demo timeline */}
      {demo && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ marginTop: 0, fontSize: 16 }}>Live demo timeline</h2>
          <div className="demo-grid">
            {demo.scenarios.map((s) => {
              const recovered = s.revenue_recovered > 0;
              return (
                <div key={s.id} className="demo-scenario">
                  <div className="demo-scenario-header">
                    <div>
                      <strong>{s.id} — {s.name}</strong>
                      <p className="subtitle" style={{ margin: "2px 0 0" }}>{s.description}</p>
                    </div>
                    <span className={`pill ${recovered ? "VERIFIED" : "BLOCKED"}`}>
                      {recovered ? "RECOVERED" : "BLOCKED"}
                    </span>
                  </div>
                  <p className="mono" style={{ margin: "6px 0 2px" }}>trace {s.trace_id}</p>
                  <p style={{ margin: "0 0 10px", fontSize: 13 }}>
                    At risk {inr(s.revenue_at_risk)} ·{" "}
                    <span style={{ color: recovered ? "var(--good)" : "var(--bad)" }}>
                      Recovered {inr(s.revenue_recovered)}
                    </span>{" "}
                    · {s.action}
                  </p>
                  <div className="pipeline">
                    {s.steps.map((st, idx) => {
                      const shown = steps
                        .slice(0, visible)
                        .some((x) => x.title === st.title && x.scenario === s.id);
                      if (!shown && visible <= idx) return null;
                      const isGood = ["VERIFIED", "PAYMENT_SUCCESS", "ALTERNATE_PAYMENT", "SAFE_RETRY"].includes(st.decision);
                      const isBad = ["STOP", "BLOCKED", "NO_ACTION"].includes(st.decision);
                      return (
                        <div
                          className={`stage ${isGood ? "stage--good" : isBad ? "stage--bad" : ""}`}
                          key={`${s.id}-${idx}`}
                        >
                          <h3>{st.title}</h3>
                          <div className="mono">
                            {st.agent} · conf {(st.confidence * 100).toFixed(0)}%
                          </div>
                          <div style={{ fontWeight: 600, marginTop: 2 }}>{st.decision}</div>
                          <div className="subtitle">{st.explanation}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Incident feed */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0, fontSize: 16 }}>Live incident feed</h2>
          {incidents.length > 0 && (
            <span className="subtitle">{incidents.length} incident{incidents.length !== 1 ? "s" : ""}</span>
          )}
        </div>
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
                <td className="mono" style={{ fontSize: 11 }}>{i.incident_id}</td>
                <td>{i.merchant_id}</td>
                <td>{inr(i.amount)}</td>
                <td>{i.root_cause ?? "—"}</td>
                <td><span className={`pill ${i.risk_level}`}>{i.risk_level}</span></td>
                <td>{i.action}</td>
                <td><span className={`pill ${i.status}`}>{i.status}</span></td>
              </tr>
            ))}
            {incidents.length === 0 && !initialLoad && (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "32px 16px" }}>
                  <p className="subtitle" style={{ margin: 0 }}>No incidents yet</p>
                  <p className="subtitle" style={{ margin: "6px 0 0", fontSize: 11 }}>
                    The background stream will populate this automatically, or click Run live demo.
                  </p>
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
  empty,
}: {
  title: string;
  data: { t: string; v: number }[];
  color: string;
  empty?: boolean;
}) {
  return (
    <div className="card">
      <p className="chart-title">{title}</p>
      {empty ? (
        <div className="chart-empty">
          <span className="subtitle" style={{ fontSize: 11 }}>
            Accumulating data — run the demo or wait for the stream
          </span>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data}>
            <XAxis dataKey="t" hide />
            <YAxis hide />
            <Tooltip
              contentStyle={{ background: "#0e1626", border: "1px solid #1e2c48", fontSize: 12 }}
            />
            <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
