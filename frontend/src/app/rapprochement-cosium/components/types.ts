export interface ReconciliationSummary {
  total_customers: number;
  solde: number;
  solde_non_rapproche: number;
  partiellement_paye: number;
  en_attente: number;
  incoherent: number;
  info_insuffisante: number;
  total_facture: number;
  total_outstanding: number;
  total_paid: number;
}

export interface ReconciliationListItem {
  customer_id: number;
  customer_name: string;
  status: string;
  confidence: string;
  total_facture: number;
  total_outstanding: number;
  total_paid: number;
  total_secu: number;
  total_mutuelle: number;
  total_client: number;
  total_avoir: number;
  invoice_count: number;
  has_pec: boolean;
  explanation: string;
  reconciled_at: string;
}

export interface ReconciliationListResponse {
  items: ReconciliationListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnomalyItem {
  type: string;
  severity: string;
  message: string;
  invoice_number?: string;
  amount?: number;
}

export interface PaymentMatch {
  payment_id: number;
  amount: number;
  type: string;
  category: string;
  issuer_name: string;
}

export interface InvoiceReconciliation {
  invoice_id: number;
  invoice_number: string;
  invoice_date: string | null;
  total_ti: number;
  outstanding_balance: number;
  settled: boolean;
  total_paid: number;
  paid_secu: number;
  paid_mutuelle: number;
  paid_client: number;
  paid_avoir: number;
  status: string;
  payments: PaymentMatch[];
  anomalies: AnomalyItem[];
}

export interface CustomerReconciliation {
  id: number;
  customer_id: number;
  customer_name: string;
  status: string;
  confidence: string;
  total_facture: number;
  total_outstanding: number;
  total_paid: number;
  total_secu: number;
  total_mutuelle: number;
  total_client: number;
  total_avoir: number;
  invoice_count: number;
  invoices: InvoiceReconciliation[];
  anomalies: AnomalyItem[];
  explanation: string;
}

export type FilterTab = "tous" | "solde" | "solde_non_rapproche" | "partiellement_paye" | "en_attente" | "incoherent";

export const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: "tous", label: "Tous" },
  { key: "solde", label: "Soldes" },
  { key: "solde_non_rapproche", label: "Non rapproches" },
  { key: "partiellement_paye", label: "Partiellement payes" },
  { key: "en_attente", label: "En attente" },
  { key: "incoherent", label: "Incoherents" },
];

export const CONFIDENCE_COLORS: Record<string, string> = {
  certain: "bg-emerald-100 text-emerald-700",
  probable: "bg-blue-100 text-blue-700",
  partiel: "bg-amber-100 text-amber-700",
  incertain: "bg-red-100 text-red-700",
};
