export interface MarketingCode {
  code: string;
  client_count: number;
  description: string;
}

export interface BatchOperation {
  id: number;
  marketing_code: string;
  label: string;
  status: "en_cours" | "termine" | "erreur";
  total_clients: number;
  clients_prets: number;
  clients_incomplets: number;
  clients_en_conflit: number;
  clients_erreur: number;
  started_at: string;
  completed_at: string | null;
}

export interface BatchItem {
  id: number;
  customer_id: number;
  customer_name: string;
  status: "en_attente" | "en_cours" | "pret" | "incomplet" | "conflit" | "erreur";
  completude_score: number;
  errors_count: number;
  warnings_count: number;
  pec_preparation_id: number | null;
  error_message: string | null;
}

export interface BatchSummary {
  batch: BatchOperation;
  items: BatchItem[];
}
