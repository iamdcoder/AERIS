import { useEffect, useRef, useState } from "react";

function defaultWebSocketUrl() {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }

  const httpBase =
    import.meta.env.VITE_API_URL ||
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:8000";

  return String(httpBase).replace(/^http/, "ws").replace(/\/+$/, "") + "/ws/airspace";
}

export function useWebSocket({ enabled = true } = {}) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);
  const socketRef = useRef(null);
  const retryRef = useRef(null);
  const attemptsRef = useRef(0);

  useEffect(() => {
    if (!enabled || typeof window === "undefined" || !window.WebSocket) {
      return undefined;
    }

    let disposed = false;

    const connect = () => {
      if (disposed) return;

      const socket = new WebSocket(defaultWebSocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        attemptsRef.current = 0;
        setConnected(true);
        setError(null);
        socket.send("ping");
      };

      socket.onmessage = (event) => {
        try {
          setLastMessage(JSON.parse(event.data));
        } catch {
          setLastMessage({ type: "TEXT", data: event.data });
        }
      };

      socket.onerror = () => {
        setError("Realtime stream unavailable; REST remains authoritative.");
      };

      socket.onclose = () => {
        setConnected(false);
        if (disposed) return;
        const delay = Math.min(8000, 500 * (2 ** Math.min(attemptsRef.current, 4)));
        attemptsRef.current += 1;
        retryRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (retryRef.current) window.clearTimeout(retryRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [enabled]);

  return { connected, lastMessage, error };
}
