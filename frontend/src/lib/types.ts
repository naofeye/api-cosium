// Types API centralisés pour OptiFlow AI

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
  created_at: string;
}

// --- Client ---
export interface Customer {
  id: number;
  first_name: string;
  last_name: string;
  birth_date: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  social_security_number: string | null;
  notes: string | null;
  avatar_url: string | null;
  created_at: string | null;
  updated_at: string | null;
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

// --- Payment ---
export interface PaymentItem {
  id: number;
  payer_type: string;
  amount_due: number;
  amount_paid: number;
  status: string;
}

export interface PaymentFull {
  id: number;
  case_id: number;
  facture_id: number | null;
  payer_type: string;
  mode_paiement: string | null;
  reference_externe: string | null;
  date_paiement: string | null;
  amount_due: number;
  amount_paid: number;
  status: string;
  created_at: string | null;
}

// --- Devis ---
export interface DevisLigne {
  id: number;
  designation: string;
  quantite: number;
  prix_unitaire_ht: number;
  taux_tva: number;
  montant_ht: number;
  montant_ttc: number;
}

export interface Devis {
  id: number;
  case_id: number;
  numero: string;
  status: string;
  montant_ht: number;
  tva: number;
  montant_ttc: number;
  part_secu: number;
  part_mutuelle: number;
  reste_a_charge: number;
  created_at: string;
  updated_at: string | null;
}

export interface DevisDetail extends Devis {
  lignes: DevisLigne[];
  customer_name: string | null;
}

// --- Facture ---
export interface Facture {
  id: number;
  case_id: number;
  devis_id: number;
  numero: string;
  date_emission: string;
  montant_ht: number;
  tva: number;
  montant_ttc: number;
  status: string;
  created_at: string;
  customer_name: string | null;
}

export interface FactureDetail extends Facture {
  lignes: DevisLigne[];
  devis_numero: string | null;
}

// --- PEC ---
export interface PecRequest {
  id: number;
  case_id: number;
  organization_id: number;
  facture_id: number | null;
  montant_demande: number;
  montant_accorde: number | null;
  status: string;
  created_at: string;
  organization_name: string | null;
  customer_name: string | null;
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

// --- Bank Transaction ---
export interface BankTransaction {
  id: number;
  date: string;
  libelle: string;
  montant: number;
  reference: string | null;
  source_file: string | null;
  reconciled: boolean;
  reconciled_payment_id: number | null;
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
}

// --- Cosium Invoice ---
export interface CosiumInvoice {
  id: number;
  cosium_id: number;
  invoice_number: string;
  invoice_date: string | null;
  customer_name: string;
  customer_id: number | null;
  type: string;
  total_ti: number;
  outstanding_balance: number;
  share_social_security: number;
  share_private_insurance: number;
  settled: boolean;
  archived: boolean;
  site_id: number | null;
  synced_at: string;
}

// --- Analytics ---
export interface FinancialKPIs {
  ca_total: number;
  montant_facture: number;
  montant_encaisse: number;
  reste_a_encaisser: number;
  taux_recouvrement: number;
}

export interface AgingBucket {
  tranche: string;
  client: number;
  mutuelle: number;
  secu: number;
  total: number;
}

export interface DashboardSummary {
  cases_count: number;
  documents_count: number;
  alerts_count: number;
  total_due: number;
  total_paid: number;
  remaining: number;
}

// --- Generic API ---
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    field?: string;
  };
}
