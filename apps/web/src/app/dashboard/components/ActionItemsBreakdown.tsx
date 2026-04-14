"use client";

import Link from "next/link";
import useSWR from "swr";
import { Zap, FolderOpen, AlertTriangle, FileText, CalendarClock, CreditCard, RefreshCw } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface ActionItemsResponse {
  total: number;
  counts: Record<string, number>;
}

interface CategoryConfig {
  label: string;
  icon: LucideIcon;
  bg: string;
  text: string;
  description: string;
}

const CATEGORY_CONFIG: Record<string, CategoryConfig> = {
  dossier_incomplet: {
    label: "Dossiers incomplets",
    icon: FolderOpen,
    bg: "bg-amber-50 border-amber-200",
    text: "text-amber-900",
    description: "Pieces obligatoires manquantes",
  },
  impaye_cosium: {
    label: "Impayes Cosium",
    icon: AlertTriangle,
    bg: "bg-red-50 border-red-200",
    text: "text-red-900",
    description: "Factures en retard > 30j",
  },
  devis_dormant: {
    label: "Devis dormants",
    icon: FileText,
    bg: "bg-blue-50 border-blue-200",
    text: "text-blue-900",
    description: "Devis non transformes > 15j",
  },
  rdv_demain: {
    label: "RDV demain",
    icon: CalendarClock,
    bg: "bg-emerald-50 border-emerald-200",
    text: "text-emerald-900",
    description: "Rappel client recommande",
  },
  paiement_retard: {
    label: "Paiements en attente",
    icon: CreditCard,
    bg: "bg-orange-50 border-orange-200",
    text: "text-orange-900",
    description: "Reste a payer",
  },
  renouvellement: {
    label: "Renouvellements",
    icon: RefreshCw,
    bg: "bg-purple-50 border-purple-200",
    text: "text-purple-900",
    description: "Clients sans achat > 2 ans",
  },
};

export function ActionItemsBreakdown() {
  const { data, error, isLoading } = useSWR<ActionItemsResponse>(
    "/action-items?status=pending&limit=1",
    { refreshInterval: 60000 },
  );

  if (isLoading || error || !data || !data.counts) return null;

  const entries = Object.entries(data.counts).filter(([, v]) => v > 0);
  if (entries.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Zap className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
          Actions par categorie
        </h3>
        <Link
          href="/actions"
          className="ml-auto rounded-full bg-red-100 text-red-700 px-2.5 py-0.5 text-xs font-bold tabular-nums hover:bg-red-200 transition-colors"
        >
          {data.total} au total →
        </Link>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        {entries.map(([type, count]) => {
          const cfg = CATEGORY_CONFIG[type] ?? {
            label: type.replace(/_/g, " "),
            icon: Zap,
            bg: "bg-gray-50 border-gray-200",
            text: "text-gray-900",
            description: "",
          };
          const Icon = cfg.icon;
          return (
            <Link
              key={type}
              href={`/actions?type=${encodeURIComponent(type)}`}
              className={`flex items-center gap-3 rounded-lg border p-3 transition-all hover:shadow-md hover:-translate-y-0.5 ${cfg.bg}`}
            >
              <Icon className={`h-6 w-6 shrink-0 ${cfg.text}`} aria-hidden="true" />
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium truncate ${cfg.text}`}>{cfg.label}</p>
                {cfg.description && (
                  <p className="text-[10px] text-text-secondary truncate">{cfg.description}</p>
                )}
              </div>
              <span className={`text-xl font-bold tabular-nums ${cfg.text}`}>{count}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
