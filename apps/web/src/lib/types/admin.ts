/**
 * Strict TypeScript types for the admin API responses.
 *
 * These interfaces mirror the Pydantic schemas defined in:
 *   backend/app/domain/schemas/admin.py
 *   backend/app/domain/schemas/sync.py
 *   backend/app/api/routers/admin_health.py (inline models)
 */

// ---------------------------------------------------------------------------
// GET /api/v1/admin/health
// ---------------------------------------------------------------------------

export interface ServiceStatus {
  status: "ok" | "degraded" | "error";
  response_ms?: number;
  error?: string;
}

export interface HealthCheckResponse {
  status: "healthy" | "degraded";
  version?: string;
  services: Record<string, ServiceStatus>;
  components?: Record<string, ServiceStatus>;
  uptime_seconds?: number;
}

// ---------------------------------------------------------------------------
// GET /api/v1/admin/metrics
// ---------------------------------------------------------------------------

export interface MetricsTotals {
  clients: number;
  dossiers: number;
  factures: number;
  paiements: number;
}

export interface MetricsActivity {
  actions_last_hour: number;
  active_users_last_hour: number;
}

export interface MetricsResponse {
  totals: MetricsTotals & { users?: number };
  activity: MetricsActivity;
}

// ---------------------------------------------------------------------------
// GET /api/v1/admin/data-quality
// ---------------------------------------------------------------------------

export interface DataQualityEntity {
  total: number;
  linked: number;
  orphan: number;
  link_rate: number;
}

export interface ExtractionStats {
  total_documents: number;
  total_extracted: number;
  extraction_rate: number;
  by_type: Record<string, number>;
}

export interface DataQualityResponse {
  invoices: DataQualityEntity;
  payments: DataQualityEntity;
  documents: DataQualityEntity;
  prescriptions: DataQualityEntity;
  extractions?: ExtractionStats;
}

// ---------------------------------------------------------------------------
// GET /api/v1/admin/cosium-test
// ---------------------------------------------------------------------------

export interface CosiumConnectionTestResponse {
  connected: boolean;
  error: string | null;
  tenant: string;
  customers_total: number | null;
}

// ---------------------------------------------------------------------------
// POST /api/v1/admin/cosium-cookies
// ---------------------------------------------------------------------------

export interface CosiumCookiesPayload {
  access_token: string;
  device_credential: string;
}

export interface CosiumCookiesResponse {
  status: string;
  message: string;
}

// ---------------------------------------------------------------------------
// GET /api/v1/sync/status
// ---------------------------------------------------------------------------

export interface SyncStatusResponse {
  configured: boolean;
  authenticated: boolean;
  erp_type: string;
  tenant: string | null;
  tenant_name: string | null;
  base_url: string;
  last_sync_at: string | null;
  first_sync_done: boolean;
}

// ---------------------------------------------------------------------------
// Audit log entry (used by activity feed & chart)
// ---------------------------------------------------------------------------

export interface AuditLogEntry {
  id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}
