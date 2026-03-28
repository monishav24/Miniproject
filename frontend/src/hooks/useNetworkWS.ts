import { useEffect, useRef, useState, useCallback } from 'react';
import type { NetworkSnapshot, RCACause, Alert } from '../types';

interface WSMessage {
  type: string;
  data?: NetworkSnapshot;
  rca?: RCACause[];
  alerts?: Alert[];
  action?: string;
}

interface UseNetworkWSReturn {
  snapshot: NetworkSnapshot | null;
  rca: RCACause[];
  alerts: Alert[];
  connected: boolean;
  triggerSurge: (duration?: number) => void;
}

const WS_URL = `ws://${window.location.hostname}:8000/ws`;

export function useNetworkWS(): UseNetworkWSReturn {
  const [snapshot, setSnapshot] = useState<NetworkSnapshot | null>(null);
  const [rca, setRca]           = useState<RCACause[]>([]);
  const [alerts, setAlerts]     = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef  = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (ev) => {
        try {
          const msg: WSMessage = JSON.parse(ev.data);
          if (msg.type === 'snapshot') {
            if (msg.data) setSnapshot(msg.data);
            if (msg.rca)  setRca(msg.rca);
            if (msg.alerts) setAlerts(msg.alerts);
          }
        } catch {/* ignore */}
      };

      ws.onclose = () => {
        setConnected(false);
        retryRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {/* ignore */}
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const triggerSurge = useCallback((duration = 15) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'surge', duration }));
    } else {
      fetch('/api/control/surge', { method: 'POST', body: new URLSearchParams({ duration: String(duration) }) });
    }
  }, []);

  return { snapshot, rca, alerts, connected, triggerSurge };
}
