"use client";

import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  brouillon: "bg-gray-100 text-gray-700",
  draft: "bg-gray-100 text-gray-700",
  en_cours: "bg-blue-100 text-blue-700",
  complet: "bg-emerald-100 text-emerald-700",
  archive: "bg-gray-100 text-gray-500",
  documents_missing: "bg-amber-100 text-amber-700",
  envoye: "bg-blue-100 text-blue-700",
  signe: "bg-emerald-100 text-emerald-700",
  refuse: "bg-red-100 text-red-700",
  annule: "bg-gray-100 text-gray-500",
  expire: "bg-amber-100 text-amber-700",
  facture: "bg-blue-100 text-blue-700",
  a_facturer: "bg-amber-100 text-amber-700",
  facturee: "bg-blue-100 text-blue-700",
  payee: "bg-emerald-100 text-emerald-700",
  paid: "bg-emerald-100 text-emerald-700",
  partial: "bg-amber-100 text-amber-700",
  partiellement_payee: "bg-amber-100 text-amber-700",
  impayee: "bg-red-100 text-red-700",
  pending: "bg-amber-100 text-amber-700",
  en_attente: "bg-amber-100 text-amber-700",
  soumise: "bg-blue-100 text-blue-700",
  acceptee: "bg-emerald-100 text-emerald-700",
  refusee: "bg-red-100 text-red-700",
  recu: "bg-emerald-100 text-emerald-700",
  retard: "bg-red-100 text-red-700",
  rejete: "bg-red-100 text-red-700",
  planifiee: "bg-gray-100 text-gray-700",
  envoyee: "bg-blue-100 text-blue-700",
  sent: "bg-blue-100 text-blue-700",
  repondue: "bg-emerald-100 text-emerald-700",
  responded: "bg-emerald-100 text-emerald-700",
  echouee: "bg-red-100 text-red-700",
  failed: "bg-red-100 text-red-700",
  waiting: "bg-amber-100 text-amber-700",
  pret: "bg-emerald-100 text-emerald-700",
  incomplet: "bg-amber-100 text-amber-700",
  conflit: "bg-red-100 text-red-700",
  erreur: "bg-gray-100 text-gray-700",
  termine: "bg-emerald-100 text-emerald-700",
};

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
  const colors = STATUS_COLORS[status] ?? "bg-gray-100 text-gray-700";
  const label = labelOverride ?? LABELS[status] ?? status.replace(/_/g, " ");
  return (
    <span
      role="status"
      aria-label={`Statut : ${label}`}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        colors,
        className,
      )}
    >
      {label}
    </span>
  );
}
