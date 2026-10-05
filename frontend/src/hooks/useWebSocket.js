import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  buildOperationsWebSocketUrl,
  fetchLiveOperations,
} from "../lib/api";

export function useWebSocket({
  enabled = true,
  pollIntervalMs = 1500,
  reconnectDelayMs = 4000,
} = {}) {
  const [snapshot, setSnapshot] = useState(null);
  const [connected, setConnected] = useState(false);
  const [transport, setTransport] = useState("OFFLINE");

  const socketRef = useRef(null);
  const pollTimerRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectScheduledRef = useRef(false);
  const stoppedRef = useRef(false);
  const connectionGenerationRef = useRef(0);

  const clearTimers = useCallback(() => {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    reconnectScheduledRef.current = false;
  }, []);

  const closeSocket = useCallback(() => {
    const socket = socketRef.current;
    socketRef.current = null;

    if (!socket) {
      return;
    }

    socket.onopen = null;
    socket.onmessage = null;
    socket.onerror = null;
    socket.onclose = null;

    try {
      socket.close();
    } catch {
      // The browser may already have closed the connection.
    }
  }, []);

  const startPolling = useCallback(() => {
    if (!enabled || stoppedRef.current) {
      return;
    }

    if (pollTimerRef.current !== null) {
      return;
    }

    const poll = async () => {
      const result = await fetchLiveOperations();

      if (stoppedRef.current) {
        return;
      }

      if (result.ok) {
        setSnapshot(result.data);
        setConnected(true);
        setTransport("POLLING");
      } else {
        setConnected(false);
        setTransport("OFFLINE");
      }
    };

    void poll();
    pollTimerRef.current = window.setInterval(
      poll,
      Math.max(1000, pollIntervalMs),
    );
  }, [enabled, pollIntervalMs]);

  const scheduleReconnect = useCallback(
    (connectFn) => {
      if (
        stoppedRef.current ||
        reconnectScheduledRef.current
      ) {
        return;
      }

      reconnectScheduledRef.current = true;
      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null;
        reconnectScheduledRef.current = false;
        connectFn();
      }, reconnectDelayMs);
    },
    [reconnectDelayMs],
  );

  const connect = useCallback(() => {
    if (!enabled || stoppedRef.current) {
      return;
    }

    clearTimers();
    closeSocket();

    const generation = ++connectionGenerationRef.current;
    let socket;

    try {
      socket = new WebSocket(buildOperationsWebSocketUrl());
    } catch {
      setConnected(false);
      setTransport("POLLING");
      startPolling();
      scheduleReconnect(connect);
      return;
    }

    socketRef.current = socket;

    socket.onopen = () => {
      if (
        stoppedRef.current ||
        generation !== connectionGenerationRef.current
      ) {
        closeSocket();
        return;
      }

      setConnected(true);
      setTransport("WEBSOCKET");
    };

    socket.onmessage = (message) => {
      if (
        stoppedRef.current ||
        generation !== connectionGenerationRef.current
      ) {
        return;
      }

      try {
        const data = JSON.parse(message.data);

        if (data.type === "heartbeat") {
          return;
        }

        setSnapshot(data);
        setConnected(true);
        setTransport("WEBSOCKET");
      } catch {
        // Ignore malformed packets and preserve the last good snapshot.
      }
    };

    socket.onerror = () => {
      if (
        stoppedRef.current ||
        generation !== connectionGenerationRef.current
      ) {
        return;
      }

      setConnected(false);
      setTransport("POLLING");
      startPolling();
    };

    socket.onclose = () => {
      if (generation !== connectionGenerationRef.current) {
        return;
      }

      if (socketRef.current === socket) {
        socketRef.current = null;
      }

      if (stoppedRef.current) {
        return;
      }

      setConnected(false);
      setTransport("POLLING");
      startPolling();
      scheduleReconnect(connect);
    };
  }, [
    clearTimers,
    closeSocket,
    enabled,
    scheduleReconnect,
    startPolling,
  ]);

  useEffect(() => {
    stoppedRef.current = false;

    // Defer the initial socket creation by one turn so React 18/19
    // StrictMode can clean up its first effect pass without creating and
    // immediately aborting a real WebSocket connection. This avoids the
    // noisy 'closed before the connection is established' browser error
    // during development while preserving the live WebSocket transport.
    const initialConnectTimer = window.setTimeout(() => {
      connect();
    }, 0);

    return () => {
      window.clearTimeout(initialConnectTimer);
      stoppedRef.current = true;
      clearTimers();
      closeSocket();
      connectionGenerationRef.current += 1;
      setConnected(false);
      setTransport("OFFLINE");
    };
  }, [clearTimers, closeSocket, connect]);

  return {
    snapshot,
    connected,
    transport,
    reconnect: connect,
  };
}
