/**
 * RealtimeContext — single WebSocket connection shared across the whole app.
 *
 * Consumers call `useRealtime()` to get:
 *   - connected        boolean
 *   - feed             LiveEvent[]   (last 120 events, newest first)
 *   - latestMetrics    Metrics | null
 *   - latestIncident   WSIncidentEvent | null
 */
import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import type {
  LiveEvent,
  Metrics,
  WSEvent,
  WSIncidentEvent,
} from "../types";

const WS_URL = (() => {
  const api = import.meta.env.VITE_API_URL ?? "";
  if (api) {
    return api.replace(/^http/, "ws") + "/ws";
  }
  // Same-origin fallback — works in both dev (proxy) and prod.
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws`;
})();

const MAX_FEED = 120;

type Ctx = {
  connected: boolean;
  feed: LiveEvent[];
  latestMetrics: Metrics | null;
  latestIncident: WSIncidentEvent | null;
};

const RealtimeContext = createContext<Ctx>({
  connected: false,
  feed: [],
  latestMetrics: null,
  latestIncident: null,
});

let _idSeq = 0;
function nextId() {
  return String(++_idSeq);
}

function toFeedEntry(ev: WSEvent): LiveEvent | null {
  switch (ev.type) {
    case "incident":
      return {
        id: nextId(),
        ts: ev.ts,
        kind: "incident",
        label: `${ev.incident_id}`,
        sub: `${ev.root_cause} · ${ev.merchant_id}`,
        badge: ev.risk_level,
        badgeClass: ev.risk_level,
      };
    case "agent_step":
      return {
        id: nextId(),
        ts: ev.ts,
        kind: "agent_step",
        label: ev.agent,
        sub: `${ev.event} → ${ev.decision}`,
        badge: ev.ok ? "ok" : "fallback",
        badgeClass: ev.ok ? "LOW" : "MEDIUM",
      };
    case "transaction":
      return {
        id: nextId(),
        ts: ev.ts,
        kind: "transaction",
        label: ev.status,
        sub: `${ev.gateway} · ₹${ev.amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`,
        badge: ev.risk_score > 0.7 ? "HIGH" : undefined,
        badgeClass: ev.risk_score > 0.7 ? "HIGH" : undefined,
      };
    case "system":
      return {
        id: nextId(),
        ts: ev.ts,
        kind: "system",
        label: ev.message,
        sub: ev.level,
      };
    case "connected":
      return {
        id: nextId(),
        ts: ev.ts,
        kind: "connected",
        label: "Stream connected",
        sub: ev.message,
      };
    default:
      return null;
  }
}

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const [feed, setFeed] = useState<LiveEvent[]>([]);
  const [latestMetrics, setLatestMetrics] = useState<Metrics | null>(null);
  const [latestIncident, setLatestIncident] = useState<WSIncidentEvent | null>(null);

  const handleMessage = useCallback((ev: WSEvent) => {
    if (ev.type === "ping") return;

    if (ev.type === "metrics") {
      setLatestMetrics(ev.metrics);
      return;
    }

    if (ev.type === "incident") {
      setLatestIncident(ev);
    }

    const entry = toFeedEntry(ev);
    if (entry) {
      setFeed((prev) => [entry, ...prev].slice(0, MAX_FEED));
    }
  }, []);

  const { connected } = useWebSocket(WS_URL, { onMessage: handleMessage });

  return (
    <RealtimeContext.Provider value={{ connected, feed, latestMetrics, latestIncident }}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  return useContext(RealtimeContext);
}
