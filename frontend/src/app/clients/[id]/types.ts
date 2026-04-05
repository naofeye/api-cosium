// Types specific to the Client 360 detail page

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

export interface CosiumPrescriptionSummary {
  id: number;
  cosium_id: number;
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
  spectacles_json: string | null;
}

export interface CosiumPaymentSummary {
  id: number;
  cosium_id: number;
  amount: number;
  type: string;
  due_date: string | null;
  issuer_name: string;
  bank: string;
  site_name: string;
  payment_number: string;
  invoice_cosium_id: number | null;
}

export interface CosiumCalendarSummary {
  id: number;
  cosium_id: number;
  start_date: string | null;
  end_date: string | null;
  subject: string;
  category_name: string;
  category_color: string;
  status: string;
  canceled: boolean;
  missed: boolean;
  observation: string | null;
  site_name: string | null;
}

export interface EquipmentItem {
  prescription_id: number;
  prescription_date: string | null;
  label: string;
  brand: string;
  type: string;
}

export interface CosiumDataBundle {
  prescriptions: CosiumPrescriptionSummary[];
  cosium_payments: CosiumPaymentSummary[];
  calendar_events: CosiumCalendarSummary[];
  equipments: EquipmentItem[];
  correction_actuelle: CorrectionActuelle | null;
  total_ca_cosium: number;
  last_visit_date: string | null;
  customer_tags: string[];
}

export interface Client360 {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  birth_date: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  social_security_number: string | null;
  avatar_url: string | null;
  cosium_id: string | number | null;
  created_at: string | null;
  dossiers: { id: number; statut: string; source: string; created_at: string }[];
  devis: { id: number; numero: string; statut: string; montant_ttc: number; reste_a_charge: number }[];
  factures: { id: number; numero: string; statut: string; montant_ttc: number; date_emission: string }[];
  paiements: {
    id: number;
    payeur: string;
    mode: string | null;
    montant_du: number;
    montant_paye: number;
    statut: string;
  }[];
  documents: { id: number; type: string; filename: string; uploaded_at: string }[];
  pec: { id: number; statut: string; montant_demande: number; montant_accorde: number | null }[];
  consentements: { canal: string; consenti: boolean }[];
  interactions: {
    id: number;
    type: string;
    direction: string;
    subject: string;
    content: string | null;
    created_at: string;
  }[];
  cosium_invoices: {
    cosium_id: number;
    invoice_number: string;
    invoice_date: string | null;
    type: string;
    total_ti: number;
    outstanding_balance: number;
    share_social_security: number;
    share_private_insurance: number;
    settled: boolean;
  }[];
  cosium_data?: CosiumDataBundle | null;
  resume_financier?: { total_facture: number; total_paye: number; reste_du: number; taux_recouvrement: number } | null;
}
