import Cookies from "js-cookie";

const TENANT_ID_KEY = "optiflow_tenant_id";
const TENANT_NAME_KEY = "optiflow_tenant_name";
const TENANTS_KEY = "optiflow_tenants";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

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
  Cookies.set(TENANT_ID_KEY, String(tenantId), { sameSite: "lax" });
  Cookies.set(TENANT_NAME_KEY, tenantName, { sameSite: "lax" });
  Cookies.set(TENANTS_KEY, JSON.stringify(availableTenants), { sameSite: "lax" });
}

// --- Login / Switch / Refresh / Logout ---

export interface LoginResult {
  role: string;
  tenant_id: number;
  tenant_name: string;
  available_tenants: AvailableTenant[];
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.error?.message || data?.message || "Email ou mot de passe incorrect");
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
  setTenantInfo(tenantId, tenantName, tenants);
  return {
    role: data.role,
    tenant_id: tenantId,
    tenant_name: tenantName,
    available_tenants: tenants,
  };
}

export async function refreshAccessToken(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    return res.ok || res.status === 204;
  } catch {
    return false;
  }
}

export function logout() {
  fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  }).catch((err) => {
    console.error("[Auth] Erreur lors de la deconnexion:", err);
  });
  clearAuthState();
}
