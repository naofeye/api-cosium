export interface SignupResponse {
  access_token: string;
  refresh_token: string;
  tenant_id: number;
  tenant_name: string;
  user_id: number;
  role: string;
}

export interface ConnectCosiumResponse {
  status: string;
}

export interface SyncDetail {
  customers: number;
  invoices: number;
  products: number;
}

export interface FirstSyncResponse {
  status: string;
  details: SyncDetail;
}

export interface FieldErrors {
  company_name?: string;
  owner_email?: string;
  owner_password?: string;
  owner_first_name?: string;
  owner_last_name?: string;
  phone?: string;
}

export interface CosiumFieldErrors {
  cosium_tenant?: string;
  cosium_login?: string;
  cosium_password?: string;
}

export function validateEmail(email: string): string | undefined {
  if (!email.trim()) return "L'adresse email est requise";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Adresse email invalide";
  return undefined;
}

export function validatePassword(password: string): string | undefined {
  if (!password) return "Le mot de passe est requis";
  if (password.length < 8) return "Le mot de passe doit contenir au moins 8 caracteres";
  return undefined;
}

export function validateRequired(value: string, label: string): string | undefined {
  if (!value.trim()) return `${label} est requis`;
  return undefined;
}
