// Types Client / Customer / User / Auth

// --- Auth ---
export interface TenantInfo {
  id: number;
  name: string;
  slug: string;
  role: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: string;
  tenant_id: number | null;
  tenant_name: string | null;
  available_tenants: TenantInfo[];
}

// --- User ---
export interface User {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
}

// --- Client Completeness ---
export interface ClientCompletenessScore {
  score: number;
  fields: Record<string, boolean>;
}

// --- Client ---
export interface Customer {
  id: number;
  cosium_id: string | null;
  customer_number: string | null;
  first_name: string;
  last_name: string;
  birth_date: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  street_number: string | null;
  street_name: string | null;
  city: string | null;
  postal_code: string | null;
  social_security_number: string | null;
  optician_name: string | null;
  ophthalmologist_id: string | null;
  mobile_phone_country: string | null;
  site_id: number | null;
  notes: string | null;
  avatar_url: string | null;
  created_at: string | null;
  updated_at: string | null;
  deleted_at: string | null;
  completeness: ClientCompletenessScore | null;
}

export interface CustomerCreate {
  first_name: string;
  last_name: string;
  birth_date?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  city?: string | null;
  postal_code?: string | null;
  social_security_number?: string | null;
  notes?: string | null;
}

// --- Case ---
export interface Case {
  id: number;
  customer_name: string;
  status: string;
  source: string | null;
  created_at: string | null;
  missing_docs: number | null;
}

export interface CaseDetail {
  id: number;
  customer_name: string;
  status: string;
  source: string | null;
  phone: string | null;
  email: string | null;
  documents: DocumentItem[];
  payments: PaymentItem[];
}

// --- Document ---
export interface DocumentItem {
  id: number;
  type: string;
  filename: string;
  uploaded_at: string;
}

// --- Notification ---
export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: number | null;
  is_read: boolean;
  created_at: string;
}

// --- Action Item ---
export interface ActionItem {
  id: number;
  type: string;
  title: string;
  description: string | null;
  entity_type: string;
  entity_id: number;
  priority: string;
  status: string;
  due_date: string | null;
  created_at: string;
}

// --- Interaction ---
export interface Interaction {
  id: number;
  client_id: number;
  case_id: number | null;
  type: string;
  direction: string;
  subject: string;
  content: string | null;
  created_by: number | null;
  created_at: string;
}

// --- Audit Log ---
export interface AuditLog {
  id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
  user_email: string | null;
}

// --- Campaign ---
export interface Campaign {
  id: number;
  name: string;
  segment_id: number;
  channel: string;
  subject: string | null;
  template: string;
  status: string;
  scheduled_at: string | null;
  sent_at: string | null;
  created_at: string;
  segment_name: string | null;
}

// --- Segment ---
export interface Segment {
  id: number;
  name: string;
  description: string | null;
  rules_json: string;
  member_count: number;
  created_at: string;
}
