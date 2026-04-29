import Cookies from "js-cookie";
import { logger } from "@/lib/logger";
import { API_BASE } from "./config";

const TENANT_ID_KEY = "optiflow_tenant_id";
const TENANT_NAME_KEY = "optiflow_tenant_name";
const TENANTS_KEY = "optiflow_tenants";

export interface AvailableTenant {
  id: number;
  name: string;
  slug: string;
  role: string;
}

// --- Auth status (no token access — httpOnly cookies handled by browser) ---

export function isAuthenticated(): boolean {
  return Cookies.get("optiflow_authenticated") === "true";
}

export function clearAuthState() {
  Cookies.remove(TENANT_ID_KEY);
  Cookies.remove(TENANT_NAME_KEY);
  Cookies.remove(TENANTS_KEY);
  Cookies.remove("optiflow_authenticated");
}

// --- Tenant info (non-sensitive, stored in JS cookies) ---

export function getTenantId(): number | undefined {
  const val = Cookies.get(TENANT_ID_KEY);
  return val ? Number(val) : undefined;
}

export function getTenantName(): string | undefined {
  return Cookies.get(TENANT_NAME_KEY);
}

export function getAvailableTenants(): AvailableTenant[] {
  const raw = Cookies.get(TENANTS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as AvailableTenant[];
  } catch {
    return [];
  }
}

function setTenantInfo(tenantId: number, tenantName: string, availableTenants: AvailableTenant[]) {
  // Cookies non-httpOnly mais Secure en prod (HTTPS) pour eviter fuite sur
  // downgrade HTTP. SameSite=lax suffit ici (pas de credential, juste UI state).
  const isHttps = typeof window !== "undefined" && window.location?.protocol === "https:";
  const opts = { sameSite: "lax" as const, secure: isHttps };
  Cookies.set(TENANT_ID_KEY, String(tenantId), opts);
  Cookies.set(TENANT_NAME_KEY, tenantName, opts);
  Cookies.set(TENANTS_KEY, JSON.stringify(availableTenants), opts);
}

// --- Login / Switch / Refresh / Logout ---

export interface LoginResult {
  role: string;
  tenant_id: number;
  tenant_name: string;
  available_tenants: AvailableTenant[];
}

export type MfaRequiredReason = "MFA_CODE_REQUIRED" | "MFA_SETUP_REQUIRED" | "MFA_CODE_INVALID";

export class MfaRequiredError extends Error {
  reason: MfaRequiredReason;
  constructor(reason: MfaRequiredReason, message?: string) {
    super(message ?? reason);
    this.name = "MfaRequiredError";
    this.reason = reason;
  }
}

const MFA_MARKERS: MfaRequiredReason[] = [
  "MFA_CODE_REQUIRED",
  "MFA_SETUP_REQUIRED",
  "MFA_CODE_INVALID",
];

export async function login(
  email: string,
  password: string,
  totpCode?: string,
): Promise<LoginResult> {
  const body: Record<string, unknown> = { email, password };
  if (totpCode) body.totp_code = totpCode;
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const rawMessage: string = data?.error?.message || data?.message || "";
    const marker = MFA_MARKERS.find((m) => rawMessage === m);
    if (marker) throw new MfaRequiredError(marker, rawMessage);
    throw new Error(rawMessage || "Email ou mot de passe incorrect");
  }
  const data = await res.json();
  // Tokens are in httpOnly cookies — we only read non-sensitive info from body
  const tenants: AvailableTenant[] = data.available_tenants ?? [];
  setTenantInfo(data.tenant_id, data.tenant_name ?? "", tenants);
  return {
    role: data.role,
    tenant_id: data.tenant_id,
    tenant_name: data.tenant_name ?? "",
    available_tenants: tenants,
  };
}

export async function switchTenant(tenantId: number): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/auth/switch-tenant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ tenant_id: tenantId }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.error?.message || data?.message || "Impossible de changer de magasin");
  }
  const data = await res.json();
  const tenants: AvailableTenant[] = data.available_tenants ?? getAvailableTenants();
  const tenantName = data.tenant_name ?? tenants.find((t) => t.id === tenantId)?.name ?? "";
  // Purge le cache API + queue offline du SW : on change d'utilisateur effectif
  // (donnees du tenant precedent ne doivent pas etre rejouees ni servies).
  if (typeof navigator !== "undefined" && navigator.serviceWorker?.controller) {
    navigator.serviceWorker.controller.postMessage({ type: "CLEAR_AUTH_DATA" });
  }
  setTenantInfo(tenantId, tenantName, tenants);
  return {
    role: data.role,
    tenant_id: tenantId,
    tenant_name: tenantName,
    available_tenants: tenants,
  };
}

// Shared promise to prevent concurrent refresh attempts (race condition fix)
let refreshPromise: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  // If a refresh is already in progress, wait for its result instead of firing another
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      return res.ok || res.status === 204;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Demande au service worker de purger le cache API + la queue offline.
 * Best-effort : pas de SW = no-op silencieux.
 */
function clearServiceWorkerAuthData() {
  if (typeof navigator !== "undefined" && navigator.serviceWorker?.controller) {
    navigator.serviceWorker.controller.postMessage({ type: "CLEAR_AUTH_DATA" });
  }
}

export function logout() {
  fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  }).catch((err) => {
    logger.error("[Auth] Erreur lors de la deconnexion:", err);
  });
  clearServiceWorkerAuthData();
  clearAuthState();
}
