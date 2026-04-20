import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string; ring: string }> = {
  brouillon: { bg: "bg-gray-50", text: "text-gray-700", dot: "bg-gray-400", ring: "ring-gray-200" },
  draft: { bg: "bg-gray-50", text: "text-gray-700", dot: "bg-gray-400", ring: "ring-gray-200" },
  en_cours: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", ring: "ring-blue-200" },
  complet: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  archive: { bg: "bg-gray-50", text: "text-gray-500", dot: "bg-gray-400", ring: "ring-gray-200" },
  documents_missing: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  envoye: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", ring: "ring-blue-200" },
  signe: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  refuse: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  annule: { bg: "bg-gray-50", text: "text-gray-500", dot: "bg-gray-400", ring: "ring-gray-200" },
  expire: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  facture: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", ring: "ring-blue-200" },
  a_facturer: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  facturee: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", ring: "ring-blue-200" },
  payee: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  paid: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  partial: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  partiellement_payee: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  impayee: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  pending: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  en_attente: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  soumise: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", ring: "ring-blue-200" },
  acceptee: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  refusee: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  recu: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  retard: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  rejete: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  planifiee: { bg: "bg-gray-50", text: "text-gray-700", dot: "bg-gray-400", ring: "ring-gray-200" },
  envoyee: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", ring: "ring-blue-200" },
  sent: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", ring: "ring-blue-200" },
  repondue: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  responded: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  echouee: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  failed: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  waiting: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  pret: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
  incomplet: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", ring: "ring-amber-200" },
  conflit: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", ring: "ring-red-200" },
  erreur: { bg: "bg-gray-50", text: "text-gray-700", dot: "bg-gray-400", ring: "ring-gray-200" },
  termine: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", ring: "ring-emerald-200" },
};

const DEFAULT_COLORS = { bg: "bg-gray-50", text: "text-gray-700", dot: "bg-gray-400", ring: "ring-gray-200" };

const LABELS: Record<string, string> = {
  draft: "Brouillon",
  brouillon: "Brouillon",
  en_cours: "En cours",
  complet: "Complet",
  archive: "Archive",
  documents_missing: "Docs manquants",
  pending: "En attente",
  paid: "Paye",
  partial: "Partiel",
  envoye: "Envoye",
  signe: "Signe",
  refuse: "Refuse",
  annule: "Annule",
  facture: "Facture",
  facturee: "Facturee",
  payee: "Payee",
  impayee: "Impayee",
  en_attente: "En attente",
  soumise: "Soumise",
  acceptee: "Acceptee",
  refusee: "Refusee",
  recu: "Recu",
  retard: "En retard",
  rejete: "Rejete",
  planifiee: "Planifiee",
  envoyee: "Envoyee",
  sent: "Envoyee",
  repondue: "Repondue",
  responded: "Repondue",
  echouee: "Echouee",
  failed: "Echouee",
  waiting: "En attente",
  pret: "Pret",
  incomplet: "Incomplet",
  conflit: "Conflit",
  erreur: "Erreur",
  termine: "Termine",
};

interface StatusBadgeProps {
  status: string;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label: labelOverride, className }: StatusBadgeProps) {
  const colors = STATUS_COLORS[status] ?? DEFAULT_COLORS;
  const label = labelOverride ?? LABELS[status] ?? status.replace(/_/g, " ");
  return (
    <span
      role="status"
      aria-label={`Statut : ${label}`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold capitalize ring-1 ring-inset",
        colors.bg,
        colors.text,
        colors.ring,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", colors.dot)} aria-hidden="true" />
      {label}
    </span>
  );
}
