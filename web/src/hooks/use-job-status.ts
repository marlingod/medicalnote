"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { WS_BASE_URL } from "@/lib/constants";
import type { EncounterStatus, JobStatusUpdate } from "@/types";

interface UseJobStatusOptions {
  enabled?: boolean;
  onStatusChange?: (status: EncounterStatus) => void;
}

export function useJobStatus(
  encounterId: string | null,
  options: UseJobStatusOptions = {}
) {
  const { enabled = true, onStatusChange } = options;
  const [status, setStatus] = useState<EncounterStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!encounterId || !enabled) return;

    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;
    if (!token) return;

    const wsUrl = `${WS_BASE_URL}/jobs/${encounterId}/?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      });

      ws.addEventListener("message", (event) => {
        try {
          const data: JobStatusUpdate = JSON.parse(event.data);
          if (data.type === "status_update") {
            setStatus(data.status);
            onStatusChange?.(data.status);
          }
        } catch {
          // Ignore malformed messages
        }
      });

      ws.addEventListener("close", () => {
        setIsConnected(false);
        // Auto-reconnect with exponential backoff
        if (
          enabled &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttemptsRef.current),
            30000
          );
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect();
          }, delay);
        }
      });

      ws.addEventListener("error", () => {
        setError("WebSocket connection error");
      });
    } catch {
      setError("Failed to create WebSocket connection");
    }
  }, [encounterId, enabled, onStatusChange]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  return { status, isConnected, error, disconnect };
}
