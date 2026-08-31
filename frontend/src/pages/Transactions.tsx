import { useEffect, useState } from "react";
import { api } from "../api";
import type { TxRecord } from "../types";

const STATUSES = [
  "ALL",
  "PAYMENT_SUCCESS",
  "PAYMENT_FAILED",
  "PAYMENT_RETRY",
  "CHECKOUT_ABANDONED",
  "SETTLEMENT_COMPLETED",
  "SETTLEMENT_PENDING",
];

const STATUS_CLASS: Record<string, string> = {
  PAYMENT_SUCCESS: "LOW",
  SETTLEMENT_COMPLETED: "LOW",
  SETTLEMENT_PENDING: "MEDIUM",
  PAYMENT_FAILED: "HIGH",
  PAYMENT_RETRY: "MEDIUM",
  CHECKOUT_ABANDONED: "MEDIUM",
};

function inr(n: number) {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function shortId(id: string) {
  return id.length > 16 ? id.slice(0, 16) + "…" : id;
}

const PAGE = 50;

export default function Transactions() {
  const [items, setItems] = useState<TxRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [status, setStatus] = useState("ALL");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(p: number, s: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.transactions({
        limit: PAGE,
        offset: p * PAGE,
        status: s === "ALL" ? undefined : s,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(0, status);
    setPage(0);
  }, [status]);

  function goPage(p: number) {
    setPage(p);
    load(p, status);
  }

  const filtered = search
    ? items.filter(
        (t) =>
          t.transaction_id.includes(search) ||
          t.merchant_id.includes(search) ||
          t.gateway.includes(search) ||
          t.payment_method.includes(search),
      )
    : items;

  const pages = Math.ceil(total / PAGE);

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Transactions</h1>
          <p className="subtitle">
            {total.toLocaleString()} synthetic transactions · {PAGE} per page
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="tx-filters">
        <input
          className="tx-search"
          placeholder="Search by ID, merchant, gateway…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="tx-status-pills">
          {STATUSES.map((s) => (
            <button
              key={s}
              className={`tx-status-btn ${status === s ? "active" : ""}`}
              onClick={() => setStatus(s)}
            >
              {s === "ALL" ? "All" : s.replace("_", " ").toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="card" style={{ marginTop: 12, padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div className="skeleton-table">
            {Array.from({ length: 8 }).map((_, i) => (
              <div className="skeleton-row" key={i}>
                <div className="skeleton-cell wide" />
                <div className="skeleton-cell" />
                <div className="skeleton-cell" />
                <div className="skeleton-cell narrow" />
                <div className="skeleton-cell narrow" />
              </div>
            ))}
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Merchant</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Gateway</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Retries</th>
                <th>Failure reason</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="subtitle" style={{ textAlign: "center", padding: 32 }}>
                    {total === 0
                      ? "No transactions yet — run the live demo to generate synthetic data."
                      : "No results match your search."}
                  </td>
                </tr>
              )}
              {filtered.map((t) => (
                <tr key={t.transaction_id}>
                  <td className="mono" style={{ fontSize: 11 }}>{shortId(t.transaction_id)}</td>
                  <td>{t.merchant_id}</td>
                  <td style={{ fontVariantNumeric: "tabular-nums" }}>{inr(t.amount)}</td>
                  <td>{t.payment_method}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{t.gateway}</td>
                  <td>
                    <span className={`pill ${STATUS_CLASS[t.status] ?? ""}`}>
                      {t.status.replace("_", " ")}
                    </span>
                  </td>
                  <td>
                    <span className="risk-bar-wrap">
                      <span
                        className="risk-bar-fill"
                        style={{ width: `${Math.round(t.risk_score * 100)}%` }}
                      />
                      <span className="risk-bar-label">{(t.risk_score * 100).toFixed(0)}%</span>
                    </span>
                  </td>
                  <td style={{ textAlign: "center" }}>{t.retry_count}</td>
                  <td className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                    {t.failure_reason ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="pagination">
          <button
            className="btn ghost"
            disabled={page === 0}
            onClick={() => goPage(page - 1)}
          >
            ← Prev
          </button>
          <span className="subtitle">
            Page {page + 1} of {pages}
          </span>
          <button
            className="btn ghost"
            disabled={page >= pages - 1}
            onClick={() => goPage(page + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
