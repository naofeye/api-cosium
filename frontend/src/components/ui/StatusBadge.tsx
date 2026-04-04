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
  expire: "bg-amber-100 text-amber-700",
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
};

const LABELS: Record<string, string> = {
  draft: "Brouillon",
  brouillon: "Brouillon",
  en_cours: "En cours",
  complet: "Complet",
  archive: "Archivé",
  documents_missing: "Docs manquants",
  pending: "En attente",
  paid: "Payé",
  partial: "Partiel",
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const colors = STATUS_COLORS[status] ?? "bg-gray-100 text-gray-700";
  const label = LABELS[status] ?? status.replace(/_/g, " ");
  return (
    <span
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
