import { CheckCircle2, XCircle, AlertTriangle, Info } from "lucide-react";

export interface PreControlResult {
  status: "pret" | "incomplet" | "conflits" | "validation_requise";
  status_label: string;
  completude_score: number;
  pieces_presentes: string[];
  pieces_manquantes: string[];
  pieces_recommandees_manquantes: string[];
  erreurs_bloquantes: string[];
  alertes_verification: string[];
  points_vigilance: string[];
  champs_confirmes: number;
  champs_deduits: number;
  champs_en_conflit: number;
  champs_manquants: number;
  champs_manuels: number;
  champs_extraits: number;
}

export const STATUS_CONFIG: Record<
  string,
  { color: string; bg: string; border: string; icon: typeof CheckCircle2; label: string }
> = {
  pret: {
    color: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    icon: CheckCircle2,
    label: "Prêt",
  },
  incomplet: {
    color: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-200",
    icon: XCircle,
    label: "Incomplet",
  },
  conflits: {
    color: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
    icon: AlertTriangle,
    label: "Conflits",
  },
  validation_requise: {
    color: "text-blue-700",
    bg: "bg-blue-50",
    border: "border-blue-200",
    icon: Info,
    label: "Validation requise",
  },
};

export const DOCUMENT_LABELS: Record<string, string> = {
  ordonnance: "Ordonnance",
  devis: "Devis signé",
  attestation_mutuelle: "Attestation mutuelle",
  carte_vitale: "Carte vitale",
  facture: "Facture",
  autre: "Autre document",
};
