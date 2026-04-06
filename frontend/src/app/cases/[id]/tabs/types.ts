export interface CompletenessItem {
  code: string;
  label: string;
  category: string;
  is_required: boolean;
  present: boolean;
}

export interface CompletenessData {
  case_id: number;
  total_required: number;
  total_present: number;
  total_missing: number;
  items: CompletenessItem[];
}

export interface CaseDetail {
  id: number;
  customer_name: string;
  status: string;
  source: string;
  created_at: string;
  phone: string | null;
  email: string | null;
}

export interface CaseDocument {
  id: number;
  type: string;
  filename: string;
  uploaded_at: string;
}

export interface PaymentItem {
  id: number;
  payer_type: string;
  amount_due: number;
  amount_paid: number;
  status: string;
}

export interface PaymentSummary {
  total_due: number;
  total_paid: number;
  remaining: number;
  items: PaymentItem[];
}

export interface CaseActivity {
  id: number;
  type: string;
  description: string;
  created_at: string;
  user_name: string | null;
}

export type Tab = "resume" | "documents" | "finances" | "historique" | "ia";
