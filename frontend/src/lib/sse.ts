const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export interface SSENotification {
  id: number;
  type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: number | null;
  created_at: string;
}

type NotificationHandler = (data: SSENotification) => void;

let eventSource: EventSource | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

const RECONNECT_DELAY_MS = 10_000;

export function connectSSE(onNotification: NotificationHandler): void {
  if (eventSource) return; // Already connected

  eventSource = new EventSource(`${API_BASE}/sse/notifications`, {
    withCredentials: true,
  });

  eventSource.onmessage = (event: MessageEvent) => {
    try {
      const data: SSENotification = JSON.parse(event.data);
      onNotification(data);
    } catch {
      // Ignore parse errors from malformed events
    }
  };

  eventSource.onerror = () => {
    disconnectSSE();
    reconnectTimer = setTimeout(() => connectSSE(onNotification), RECONNECT_DELAY_MS);
  };
}

export function disconnectSSE(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}
