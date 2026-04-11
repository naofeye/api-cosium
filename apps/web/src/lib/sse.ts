import { API_BASE } from "./config";

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
let currentHandler: NotificationHandler | null = null;
let reconnectAttempts = 0;
let isReconnecting = false;

const BASE_RECONNECT_DELAY_MS = 5_000;
const MAX_RECONNECT_DELAY_MS = 60_000;

function getReconnectDelay(): number {
  // Exponential backoff: 5s, 10s, 20s, 40s, max 60s
  const delay = Math.min(
    BASE_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempts),
    MAX_RECONNECT_DELAY_MS,
  );
  return delay;
}

export function connectSSE(onNotification: NotificationHandler): void {
  currentHandler = onNotification;

  if (eventSource) return; // Already connected

  eventSource = new EventSource(`${API_BASE}/sse/notifications`, {
    withCredentials: true,
  });

  eventSource.onmessage = (event: MessageEvent) => {
    try {
      const data: SSENotification = JSON.parse(event.data);
      // Reset reconnect counter on successful message
      reconnectAttempts = 0;
      if (currentHandler) {
        currentHandler(data);
      }
    } catch {
      // Ignore parse errors from malformed events
    }
  };

  eventSource.onopen = () => {
    reconnectAttempts = 0;
    isReconnecting = false;
  };

  eventSource.onerror = () => {
    // Close current source
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }

    // Prevent multiple simultaneous reconnection attempts from rapid onerror calls
    if (isReconnecting) return;
    isReconnecting = true;

    // Schedule reconnect with backoff
    const delay = getReconnectDelay();
    reconnectAttempts++;

    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      isReconnecting = false;
      if (currentHandler) {
        connectSSE(currentHandler);
      }
    }, delay);
  };
}

export function disconnectSSE(): void {
  currentHandler = null;
  reconnectAttempts = 0;
  isReconnecting = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}
