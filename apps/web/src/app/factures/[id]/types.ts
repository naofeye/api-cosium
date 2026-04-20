export interface FactureLigne {
  id: number;
  designation: string;
  quantite: number;
  prix_unitaire_ht: number;
  taux_tva: number;
  montant_ht: number;
  montant_ttc: number;
}

export interface FacturePayment {
  id: number;
  date: string;
  amount: number;
  method: string;
  payer_type: string;
  status: string;
}

export interface FacturePEC {
  id: number;
  status: string;
  organisme: string;
  montant_demande: number;
  montant_accepte: number | null;
}

export interface FactureDetail {
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
  montant_paye: number;
  reste_a_payer: number;
  customer_name: string | null;
  customer_email: string | null;
  devis_numero: string | null;
  lignes: FactureLigne[];
  payments: FacturePayment[];
  pec: FacturePEC | null;
}
