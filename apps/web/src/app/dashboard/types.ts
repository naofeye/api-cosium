export interface DashboardData {
  financial: {
    ca_total: number;
    montant_facture: number;
    montant_encaisse: number;
    reste_a_encaisser: number;
    taux_recouvrement: number;
  };
  aging: {
    buckets: { tranche: string; client: number; mutuelle: number; secu: number; total: number }[];
    total: number;
  };
  payers: {
    payers: {
      name: string;
      type: string;
      acceptance_rate: number;
      total_requested: number;
      total_accepted: number;
    }[];
  };
  operational: {
    dossiers_en_cours: number;
    dossiers_complets: number;
    taux_completude: number;
    pieces_manquantes: number;
  };
  commercial: {
    devis_en_cours: number;
    devis_signes: number;
    taux_conversion: number;
    panier_moyen: number;
    ca_par_mois: { mois: string; ca: number }[];
  };
  marketing: {
    campagnes_total: number;
    campagnes_envoyees: number;
    messages_envoyes: number;
  };
  cosium: {
    total_facture_cosium: number;
    total_outstanding: number;
    total_paid: number;
    invoice_count: number;
    quote_count: number;
    credit_note_count: number;
    total_devis_cosium: number;
    total_avoirs_cosium: number;
  } | null;
  cosium_counts: {
    total_clients: number;
    total_rdv: number;
    total_prescriptions: number;
    total_payments: number;
  } | null;
  cosium_ca_par_mois: { mois: string; ca: number }[];
  comparison: {
    ca_total_delta: number | null;
    montant_encaisse_delta: number | null;
    reste_a_encaisser_delta: number | null;
    taux_recouvrement_delta: number | null;
    clients_delta: number | null;
    factures_delta: number | null;
  } | null;
}

export interface RenewalData {
  total_opportunities: number;
  high_score_count: number;
  estimated_revenue: number;
}

export interface OverdueInvoice {
  id: number;
  customer_name: string;
  montant_ttc: number;
  date_emission: string;
  days_overdue: number;
}

export interface OverdueInvoicesResponse {
  items: OverdueInvoice[];
  total: number;
}

export interface DataQualityData {
  extractions?: {
    total_documents: number;
    total_extracted: number;
    extraction_rate: number;
    by_type: Record<string, number>;
  } | null;
}

export interface CalendarEvent {
  id: number | string;
  start_date: string;
  end_date?: string;
  customer_fullname: string;
  category_name: string;
  category_color: string;
}

export interface CalendarEventsResponse {
  events: CalendarEvent[];
  total: number;
}

export interface ReconciliationSummary {
  total_customers: number;
  solde: number;
  solde_non_rapproche: number;
  partiellement_paye: number;
  en_attente: number;
  incoherent: number;
  total_facture: number;
  total_outstanding: number;
}
