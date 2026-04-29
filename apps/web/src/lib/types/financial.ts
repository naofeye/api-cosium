// Types financiers : Payment, Devis, Facture, PEC, BankTransaction, Analytics

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
  valid_until: string | null;
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
