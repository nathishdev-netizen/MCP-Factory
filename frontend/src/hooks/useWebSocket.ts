import { useCallback, useEffect, useRef, useState } from "react";
import type { WSFrame } from "../types/messages";

interface UseWebSocketReturn {
  isConnected: boolean;
  sessionId: string | null;
  sendFrame: (frame: Omit<WSFrame, "timestamp">) => void;
}

export function useWebSocket(
  onFrame: (frame: WSFrame) => void
): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttempts = useRef(0);
  const sessionIdRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  // Keep onFrame ref current so the WebSocket callback always calls the latest version
  const onFrameRef = useRef(onFrame);
  onFrameRef.current = onFrame;

  const connect = useCallback(() => {
    const id = sessionIdRef.current || "new";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/${id}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setIsConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      const frame: WSFrame = JSON.parse(event.data);

      // Capture session ID from first system message
      if (
        frame.type === "system_message" &&
        frame.payload.phase === "initial" &&
        !sessionIdRef.current
      ) {
        const newId = frame.payload.message as string;
        sessionIdRef.current = newId;
        setSessionId(newId);
      }

      // Call the handler directly — no React state batching, no dropped frames
      onFrameRef.current(frame);
    };

    ws.onclose = (event) => {
      if (!mountedRef.current) return;
      setIsConnected(false);

      // Server sent 4004 = session not found (e.g., server restarted).
      // Clear the stale session ID so the next connect creates a fresh one.
      if (event.code === 4004) {
        sessionIdRef.current = null;
        setSessionId(null);
      }

      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 10000);
      reconnectAttempts.current += 1;
      reconnectTimeoutRef.current = window.setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  const sendFrame = useCallback(
    (frame: Omit<WSFrame, "timestamp">) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            ...frame,
            timestamp: new Date().toISOString(),
          })
        );
      }
    },
    []
  );

  return { isConnected, sessionId, sendFrame };
}
