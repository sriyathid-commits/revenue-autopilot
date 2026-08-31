/**
 * LiveFeed — animated real-time event ticker for the sidebar.
 * Shows the last N events streamed over WebSocket.
 */
import { useRealtime } from "../context/RealtimeContext";

const KIND_ICON: Record<string, string> = {
  incident: "⚡",
  agent_step: "🤖",
  transaction: "💳",
  system: "🔧",
  connected: "🟢",
};

function timeLabel(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso.slice(11, 19);
  }
}

export default function LiveFeed() {
  const { connected, feed } = useRealtime();

  return (
    <div className="live-feed">
      {/* Header */}
      <div className="live-feed-header">
        <span className={`live-dot ${connected ? "live-dot--on" : "live-dot--off"}`} />
        <span className="live-feed-title">
          {connected ? "Live stream" : "Reconnecting…"}
        </span>
      </div>

      {/* Event list */}
      <div className="live-feed-list">
        {feed.length === 0 && (
          <p className="live-feed-empty">Waiting for events…</p>
        )}
        {feed.slice(0, 30).map((ev) => (
          <div className="live-feed-row" key={ev.id}>
            <span className="live-feed-icon">{KIND_ICON[ev.kind] ?? "•"}</span>
            <div className="live-feed-body">
              <div className="live-feed-label">
                {ev.label}
                {ev.badge && (
                  <span className={`pill ${ev.badgeClass ?? ""}`} style={{ marginLeft: 6 }}>
                    {ev.badge}
                  </span>
                )}
              </div>
              <div className="live-feed-sub">{ev.sub}</div>
            </div>
            <span className="live-feed-time">{timeLabel(ev.ts)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
