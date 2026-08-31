import { useEffect, useState } from "react";
import { api } from "../api";
import type { HumanReview } from "../types";

function inr(n: number) {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function RiskBadge({ level }: { level: string }) {
  return <span className={`pill ${level}`}>{level}</span>;
}

function ReviewCard({
  item,
  onAction,
}: {
  item: HumanReview;
  onAction: (id: string, action: "APPROVE" | "REJECT") => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(item.review_completed);
  const [finalStatus, setFinalStatus] = useState(item.status);
  const [err, setErr] = useState<string | null>(null);

  async function handle(action: "APPROVE" | "REJECT") {
    setBusy(true);
    setErr(null);
    try {
      await onAction(item.incident_id, action);
      setDone(true);
      setFinalStatus(action === "APPROVE" ? "APPROVED" : "REJECTED");
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`review-card ${done ? "review-card--done" : ""}`}>
      {/* Header */}
      <div className="review-card-header">
        <div>
          <div className="review-card-title">
            <RiskBadge level={item.risk_level} />
            <span className="mono" style={{ fontSize: 12 }}>{item.incident_id}</span>
          </div>
          <div className="review-card-merchant">{item.merchant_id}</div>
        </div>
        <div className="review-card-amount">{inr(item.amount)}</div>
      </div>

      {/* Detail grid */}
      <div className="review-grid">
        <div className="review-cell">
          <div className="label">Cause</div>
          <div className="value-sm">{item.root_cause ?? "—"}</div>
        </div>
        <div className="review-cell">
          <div className="label">Risk</div>
          <div className="value-sm"><RiskBadge level={item.risk_level} /></div>
        </div>
        <div className="review-cell">
          <div className="label">Retries</div>
          <div className="value-sm">{item.retry_count}</div>
        </div>
        <div className="review-cell">
          <div className="label">Confidence</div>
          <div className="value-sm">{(item.confidence * 100).toFixed(0)}%</div>
        </div>
        <div className="review-cell">
          <div className="label">AI Recommendation</div>
          <div className="value-sm">{item.ai_recommendation}</div>
        </div>
        <div className="review-cell">
          <div className="label">MoneyGuard</div>
          <div className="value-sm">{item.moneyguard_decision}</div>
        </div>
      </div>

      {/* Reason */}
      <div className="review-reason">
        <span className="label" style={{ marginRight: 6 }}>Review reason:</span>
        {item.review_reason}
      </div>

      {item.moneyguard_reason && (
        <div className="review-reason" style={{ marginTop: 4, color: "var(--muted)" }}>
          <span className="label" style={{ marginRight: 6 }}>MoneyGuard:</span>
          {item.moneyguard_reason}
        </div>
      )}

      {err && <p className="error" style={{ margin: "8px 0 0" }}>{err}</p>}

      {/* Actions */}
      {done ? (
        <div className="review-done">
          <span className={`pill ${finalStatus === "APPROVED" ? "VERIFIED" : "BLOCKED"}`}>
            {finalStatus}
          </span>
          <span className="subtitle" style={{ marginLeft: 8 }}>Review completed</span>
        </div>
      ) : (
        <div className="review-actions">
          <button
            className="btn btn-approve"
            disabled={busy}
            onClick={() => handle("APPROVE")}
          >
            ✓ Approve
          </button>
          <button
            className="btn btn-reject"
            disabled={busy}
            onClick={() => handle("REJECT")}
          >
            ✕ Reject
          </button>
          {busy && <span className="subtitle" style={{ marginLeft: 8 }}>Submitting…</span>}
        </div>
      )}
    </div>
  );
}

export default function HumanReviewPage() {
  const [items, setItems] = useState<HumanReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.reviews();
      setItems(res.items);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleAction(id: string, action: "APPROVE" | "REJECT") {
    const res = await api.submitReview(id, action);
    // Update local state so the card reflects the new status immediately.
    setItems((prev) =>
      prev.map((i) => (i.incident_id === id ? res.review : i)),
    );
  }

  const pending = items.filter((i) => !i.review_completed);
  const completed = items.filter((i) => i.review_completed);

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Human Review</h1>
          <p className="subtitle">
            High-risk or uncertain incidents routed here by MoneyGuard or the Policy Engine.
            Approve or reject — <strong>test-mode only</strong>, no real money moves.
          </p>
        </div>
        <button className="btn ghost" onClick={load} disabled={loading}>
          ↻ Refresh
        </button>
      </div>

      {error && (
        <div className="error-box">
          <strong>Error</strong>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="skeleton-table" style={{ marginTop: 16 }}>
          {[1, 2, 3].map((i) => (
            <div className="skeleton-row" key={i} style={{ height: 96 }}>
              <div className="skeleton-cell" style={{ flex: 1 }} />
            </div>
          ))}
        </div>
      )}

      {!loading && items.length === 0 && (
        <div className="card" style={{ marginTop: 16, textAlign: "center", padding: 40 }}>
          <p style={{ fontSize: 28 }}>🔍</p>
          <p className="subtitle">No pending reviews</p>
          <p className="subtitle" style={{ fontSize: 11, marginTop: 4 }}>
            Run the live demo — high-risk and suspicious incidents will appear here.
          </p>
        </div>
      )}

      {!loading && pending.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="review-section-title">
            Pending ({pending.length})
          </div>
          <div className="review-list">
            {pending.map((item) => (
              <ReviewCard key={item.incident_id} item={item} onAction={handleAction} />
            ))}
          </div>
        </div>
      )}

      {!loading && completed.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div className="review-section-title" style={{ color: "var(--muted)" }}>
            Completed ({completed.length})
          </div>
          <div className="review-list">
            {completed.map((item) => (
              <ReviewCard key={item.incident_id} item={item} onAction={handleAction} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
