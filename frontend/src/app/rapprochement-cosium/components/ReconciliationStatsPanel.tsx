import { KPICard } from "@/components/ui/KPICard";
import { formatMoney } from "@/lib/format";
import {
  CheckCircle,
  AlertCircle,
  FileText,
  Users,
  Euro,
  ArrowLeftRight,
} from "lucide-react";
import type { ReconciliationSummary } from "./types";

interface ReconciliationStatsPanelProps {
  summary: ReconciliationSummary | undefined;
}

export function ReconciliationStatsPanel({ summary }: ReconciliationStatsPanelProps) {
  const totalDossiers = summary?.total_customers ?? 0;
  const soldes = summary?.solde ?? 0;
  const nonRapproches = summary?.solde_non_rapproche ?? 0;
  const partiels = summary?.partiellement_paye ?? 0;
  const incoherents = summary?.incoherent ?? 0;
  const totalFacture = summary?.total_facture ?? 0;
  const totalImpaye = summary?.total_outstanding ?? 0;
  const tauxSolde = totalDossiers > 0 ? Math.round(((soldes + nonRapproches) / totalDossiers) * 100) : 0;

  return (
    <>
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <KPICard
          icon={Users}
          label="Total dossiers"
          value={totalDossiers.toLocaleString("fr-FR")}
          color="primary"
        />
        <KPICard
          icon={CheckCircle}
          label={`Soldes (${tauxSolde}%)`}
          value={soldes.toLocaleString("fr-FR")}
          color="success"
        />
        <KPICard
          icon={ArrowLeftRight}
          label="Non rapproches"
          value={nonRapproches.toLocaleString("fr-FR")}
          color="primary"
        />
        <KPICard
          icon={AlertCircle}
          label="Partiellement payes"
          value={partiels.toLocaleString("fr-FR")}
          color="warning"
        />
        <KPICard
          icon={AlertCircle}
          label="Incoherents"
          value={incoherents.toLocaleString("fr-FR")}
          color="danger"
        />
        <KPICard
          icon={Euro}
          label="Total impaye"
          value={formatMoney(totalImpaye)}
          color={totalImpaye > 0 ? "danger" : "success"}
        />
      </div>

      {/* Summary amounts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Total facture</p>
            <p className="text-lg font-bold tabular-nums text-text-primary">{formatMoney(totalFacture)}</p>
          </div>
          <FileText className="h-8 w-8 text-gray-200" aria-hidden="true" />
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Total impaye</p>
            <p className="text-lg font-bold tabular-nums text-red-700">{formatMoney(totalImpaye)}</p>
          </div>
          <Euro className="h-8 w-8 text-red-200" aria-hidden="true" />
        </div>
      </div>
    </>
  );
}
