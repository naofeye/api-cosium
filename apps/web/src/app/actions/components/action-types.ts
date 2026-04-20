import {
  FolderOpen,
  FileText,
  Euro,
  Clock,
  AlertTriangle,
} from "lucide-react";

export interface DashboardData {
  cases_count: number;
  documents_count: number;
  alerts_count: number;
  payments_due: number;
  payments_paid: number;
  payments_remaining: number;
}

export interface ActionItem {
  id: number;
  type: string;
  title: string;
  description: string | null;
  entity_type: string;
  entity_id: number;
  priority: string;
  status: string;
  created_at: string;
}

export interface ActionItemList {
  items: ActionItem[];
  total: number;
  counts: Record<string, number>;
}

export const TYPE_LABELS: Record<string, string> = {
  dossier_incomplet: "Dossiers incomplets",
  paiement_retard: "Paiements en attente",
  pec_attente: "PEC en attente",
  relance_faire: "Relances a faire",
  devis_expiration: "Devis expirant",
  impaye_cosium: "Impayes Cosium",
  devis_dormant: "Devis dormants",
  rdv_demain: "RDV demain",
  renouvellement: "Renouvellements eligibles",
};

export const TYPE_ICONS: Record<string, typeof FolderOpen> = {
  dossier_incomplet: FolderOpen,
  paiement_retard: Euro,
  pec_attente: Clock,
  relance_faire: AlertTriangle,
  devis_expiration: FileText,
};

export const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-200",
  high: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  medium: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
  low: "bg-gray-50 text-gray-600 ring-1 ring-inset ring-gray-200",
};

export const PRIORITY_LABELS: Record<string, string> = {
  critical: "Critique",
  high: "Haute",
  medium: "Moyenne",
  low: "Basse",
};
