// Types Cosium (invoice, calendar, prescription, payment, mutuelle, doctor, document)

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

// --- Cosium Calendar Event ---
export interface CosiumCalendarEvent {
  id: number;
  start_date: string | null;
  end_date: string | null;
  subject: string;
  customer_fullname: string;
  customer_number: string;
  category_name: string;
  category_color: string;
  category_family: string;
  status: string;
  canceled: boolean;
  missed: boolean;
  observation: string;
  site_name: string;
}

// --- Cosium Prescription ---
export interface CosiumPrescription {
  id: number;
  tenant_id: number;
  cosium_id: number;
  prescription_date: string | null;
  file_date: string | null;
  customer_cosium_id: number | null;
  customer_id: number | null;
  sphere_right: number | null;
  cylinder_right: number | null;
  axis_right: number | null;
  addition_right: number | null;
  sphere_left: number | null;
  cylinder_left: number | null;
  axis_left: number | null;
  addition_left: number | null;
  spectacles_json: string | null;
  prescriber_name: string | null;
  synced_at: string;
}

// --- Cosium Payment Item ---
export interface CosiumPaymentItem {
  id: number;
  amount: number;
  type: string;
  due_date: string | null;
  issuer_name: string;
  bank: string;
  site_name: string;
  payment_number: string;
}

// --- Cosium Mutuelle ---
export interface CosiumMutuelle {
  id: number;
  name: string;
  code: string;
  phone: string;
  email: string;
  city: string;
  hidden: boolean;
  opto_amc: boolean;
}

// --- Cosium Doctor ---
export interface CosiumDoctor {
  id: number;
  firstname: string;
  lastname: string;
  civility: string;
  email: string | null;
  phone: string | null;
  rpps_number: string | null;
  specialty: string;
  optic_prescriber: boolean;
  audio_prescriber: boolean;
}

// --- Cosium Document ---
export interface CosiumDocument {
  name: string;
  id: number;
  download_url: string;
}

export interface LocalCosiumDocument {
  id: number;
  customer_cosium_id: number;
  cosium_document_id: number;
  name: string | null;
  content_type: string;
  size_bytes: number;
  synced_at: string;
  source: "local";
}

// --- Cosium Product ---
export interface CosiumProduct {
  id: number;
  cosium_id: string;
  label: string;
  code: string;
  ean_code: string;
  price: number;
  family_type: string;
}

// --- All Documents Item ---
export interface AllDocumentItem {
  id: number;
  customer_cosium_id: number;
  customer_id: number | null;
  customer_name: string | null;
  cosium_document_id: number;
  name: string | null;
  content_type: string;
  size_bytes: number;
  document_type: string | null;
  classification_confidence: number | null;
  synced_at: string | null;
}

export interface AllDocumentsResponse {
  items: AllDocumentItem[];
  total: number;
  page: number;
  page_size: number;
  total_size_bytes: number;
  type_counts: Record<string, number>;
}

export interface DocumentSyncStatus {
  total_documents: number;
  customers_with_docs: number;
  total_customers: number;
  total_size_bytes: number;
  total_size_mb: number;
  last_sync_at: string | null;
}
