/**
 * useWebSocket — typed, auto-reconnecting WebSocket hook.
 *
 * Usage:
 *   const { lastEvent, connected, error } = useWebSocket<WSEvent>(url, onMessage);
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { WSEvent } from "../types";

type Opts = {
  /** Called for every parsed message. */
  onMessage: (ev: WSEvent) => void;
  /** Milliseconds before reconnect attempt. Default 3000. */
  reconnectDelay?: number;
  /** Set false to disable auto-reconnect. Default true. */
  reconnect?: boolean;
};

type State = {
  connected: boolean;
  error: string | null;
};

export function useWebSocket(url: string, opts: Opts): State {
  const { onMessage, reconnectDelay = 3000, reconnect = true } = opts;
  const ws = useRef<WebSocket | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [state, setState] = useState<State>({ connected: false, error: null });
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (ws.current) {
      ws.current.onopen = null;
      ws.current.onmessage = null;
      ws.current.onerror = null;
      ws.current.onclose = null;
      ws.current.close();
    }

    const socket = new WebSocket(url);
    ws.current = socket;

    socket.onopen = () => {
      setState({ connected: true, error: null });
    };

    socket.onmessage = (ev: MessageEvent<string>) => {
      try {
        const data = JSON.parse(ev.data) as WSEvent;
        onMessageRef.current(data);
      } catch {
        // ignore malformed frames
      }
    };

    socket.onerror = () => {
      setState((s) => ({ ...s, error: "WebSocket error" }));
    };

    socket.onclose = () => {
      setState({ connected: false, error: null });
      if (reconnect) {
        timer.current = setTimeout(connect, reconnectDelay);
      }
    };
  }, [url, reconnect, reconnectDelay]);

  useEffect(() => {
    connect();
    return () => {
      // Cleanup on unmount — disable reconnect.
      if (timer.current) clearTimeout(timer.current);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [connect]);

  return state;
}
