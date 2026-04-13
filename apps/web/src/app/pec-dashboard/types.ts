export interface PecPreparationItem {
  id: number;
  customer_id: number;
  customer_name: string;
  devis_id: number | null;
  status: string;
  completude_score: number;
  errors_count: number;
  warnings_count: number;
  created_at: string | null;
}

export interface PecDashboardData {
  items: PecPreparationItem[];
  total: number;
  counts: Record<string, number>;
}

export const STATUS_LABELS: Record<string, string> = {
  en_preparation: "En preparation",
  prete: "Prete",
  soumise: "Soumise",
};

export const STATUS_COLORS: Record<string, string> = {
  en_preparation: "bg-amber-100 text-amber-800",
  prete: "bg-emerald-100 text-emerald-800",
  soumise: "bg-blue-100 text-blue-800",
};

export const STATUS_OPTIONS = [
  { value: "", label: "Tous les statuts" },
  { value: "en_preparation", label: "En preparation" },
  { value: "prete", label: "Prete" },
  { value: "soumise", label: "Soumise" },
];

export function formatPecDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  try {
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "-";
  }
}
