export interface Interaction {
  id: number;
  type: string;
  direction: string;
  subject: string;
  content: string | null;
  created_at: string;
}

export interface CorrectionActuelle {
  prescription_date: string | null;
  prescriber_name: string | null;
  sphere_right: number | null;
  cylinder_right: number | null;
  axis_right: number | null;
  addition_right: number | null;
  sphere_left: number | null;
  cylinder_left: number | null;
  axis_left: number | null;
  addition_left: number | null;
}

export interface CalendarEvent {
  id: number;
  start_date: string | null;
  subject: string;
  category_name: string;
  status: string;
  site_name: string | null;
}

export interface ClientMutuelleInfo {
  id: number;
  mutuelle_name: string;
  active: boolean;
  source: string;
  confidence: number;
  numero_adherent: string | null;
  type_beneficiaire: string;
  date_debut: string | null;
  date_fin: string | null;
}

export interface CosiumInvoice {
  cosium_id: number;
  invoice_number: string;
  invoice_date: string | null;
  type: string;
  total_ti: number;
  settled: boolean;
}

export interface ClientScore {
  score: number;
  category: string;
  color: string;
  ca_12m: number;
  nb_factures_12m: number;
  years_since_first_invoice: number;
  days_since_last_invoice: number | null;
  outstanding: number;
  has_mutuelle: boolean;
  is_renewable: boolean;
  breakdown: Record<string, number>;
}
