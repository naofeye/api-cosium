export interface Subscription {
  id: number;
  name: string;
  url: string;
  event_types: string[];
  is_active: boolean;
  description: string | null;
  secret_masked: string;
  created_at: string;
  updated_at: string;
}

export interface Delivery {
  id: number;
  subscription_id: number;
  tenant_id: number;
  event_id: string;
  event_type: string;
  status: string;
  attempts: number;
  last_status_code: number | null;
  last_error: string | null;
  next_retry_at: string | null;
  delivered_at: string | null;
  duration_ms: number | null;
  created_at: string;
  payload?: Record<string, unknown>;
}

export interface DeliveryList {
  items: Delivery[];
  total: number;
}

export interface AllowedEvents {
  events: string[];
}
