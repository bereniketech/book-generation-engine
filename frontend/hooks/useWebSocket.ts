"use client";

import { useEffect, useRef, useState } from "react";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws");

export interface ProgressEvent {
  type: "progress" | "chapter_ready" | "complete" | "error";
  job_id: string;
  status?: string;
  step?: string;
  progress?: number;
  chapter_id?: string;
  chapter_index?: number;
  download_url?: string;
  message?: string;
}

export function useWebSocket(jobId: string) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/v1/ws/${jobId}`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => {
        try {
          const event: ProgressEvent = JSON.parse(e.data);
          setEvents((prev) => [...prev, event]);
        } catch {
          // ignore malformed messages
        }
      };
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000); // auto-reconnect after 3s
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [jobId]);

  const latestEvent = events[events.length - 1] ?? null;
  return { events, latestEvent, connected };
}
