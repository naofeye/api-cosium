import type { CosiumDataBundle } from "../types";

export type Tab =
  | "resume"
  | "dossiers"
  | "finances"
  | "documents"
  | "marketing"
  | "historique"
  | "activite"
  | "cosium-docs"
  | "ordonnances"
  | "cosium-paiements"
  | "rendez-vous"
  | "equipements"
  | "fidelite"
  | "sav"
  | "pec"
  | "rapprochement";

export interface TabDef {
  key: Tab;
  label: string;
  count?: number;
}

export interface ClientTabsProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  clientId: string | number;
  cosiumId: string | number | null;
  cosiumData: CosiumDataBundle | null;
  dossiers: { id: number; statut: string; source: string; created_at: string }[];
  devis: { id: number; numero: string; statut: string; montant_ttc: number; reste_a_charge: number; created_at: string | null }[];
  factures: { id: number; numero: string; statut: string; montant_ttc: number; date_emission: string }[];
  paiements: { id: number; payeur: string; mode: string | null; montant_du: number; montant_paye: number; statut: string }[];
  documents: { id: number; type: string; filename: string; uploaded_at: string }[];
  consentements: { canal: string; consenti: boolean }[];
  interactions: { id: number; type: string; direction: string; subject: string; content: string | null; created_at: string }[];
  cosiumInvoices: { cosium_id: number; invoice_number: string; invoice_date: string | null; type: string; total_ti: number; outstanding_balance: number; share_social_security: number; share_private_insurance: number; settled: boolean }[];
  // Resume tab props
  firstName: string;
  lastName: string;
  phone: string | null;
  email: string | null;
  socialSecurityNumber: string | null;
  postalCode: string | null;
  city: string | null;
  renewalEligible: boolean;
  renewalMonths: number;
  // Callback for data refresh
  onDataRefresh?: () => void;
  // Historique form state
  showForm: boolean;
  onShowForm: (v: boolean) => void;
  intType: string;
  onIntTypeChange: (v: string) => void;
  intDir: string;
  onIntDirChange: (v: string) => void;
  intSubj: string;
  onIntSubjChange: (v: string) => void;
  intBody: string;
  onIntBodyChange: (v: string) => void;
  submitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
}
