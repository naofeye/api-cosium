"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { DashboardKPIs } from "./components/DashboardKPIs";
import { DashboardCharts } from "./components/DashboardCharts";
import { CosiumDataSection } from "./components/CosiumDataSection";
import { DashboardSections } from "./components/DashboardSections";
import { RenewalSection } from "./components/RenewalSection";
import { PayersTable } from "./components/PayersTable";

type PeriodKey = "today" | "7d" | "30d" | "90d";

const PERIODS: { key: PeriodKey; label: string; days: number }[] = [
  { key: "today", label: "Aujourd'hui", days: 0 },
  { key: "7d", label: "7 jours", days: 7 },
  { key: "30d", label: "30 jours", days: 30 },
  { key: "90d", label: "90 jours", days: 90 },
];

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function getDateRange(period: PeriodKey): { date_from: string; date_to: string } {
  const now = new Date();
  const date_to = formatDate(now);
  if (period === "today") {
    return { date_from: date_to, date_to };
  }
  const days = PERIODS.find((p) => p.key === period)!.days;
  const from = new Date(now);
  from.setDate(from.getDate() - days);
  return { date_from: formatDate(from), date_to };
}

interface DashboardData {
  financial: {
    ca_total: number;
    montant_facture: number;
    montant_encaisse: number;
    reste_a_encaisser: number;
    taux_recouvrement: number;
  };
  aging: {
    buckets: { tranche: string; client: number; mutuelle: number; secu: number; total: number }[];
    total: number;
  };
  payers: {
    payers: { name: string; type: string; acceptance_rate: number; total_requested: number; total_accepted: number }[];
  };
  operational: {
    dossiers_en_cours: number;
    dossiers_complets: number;
    taux_completude: number;
    pieces_manquantes: number;
  };
  commercial: {
    devis_en_cours: number;
    devis_signes: number;
    taux_conversion: number;
    panier_moyen: number;
    ca_par_mois: { mois: string; ca: number }[];
  };
  marketing: { campagnes_total: number; campagnes_envoyees: number; messages_envoyes: number };
  cosium: {
    total_facture_cosium: number;
    total_outstanding: number;
    total_paid: number;
    invoice_count: number;
    quote_count: number;
    credit_note_count: number;
  } | null;
}

interface RenewalData {
  total_opportunities: number;
  high_score_count: number;
  estimated_revenue: number;
}

export default function DashboardPage() {
  const [period, setPeriod] = useState<PeriodKey>("30d");
  const { date_from, date_to } = useMemo(() => getDateRange(period), [period]);

  const { data, error, isLoading, mutate } = useSWR<DashboardData>(
    `/analytics/dashboard?date_from=${date_from}&date_to=${date_to}`,
    { refreshInterval: 60000 },
  );
  const { data: renewalData } = useSWR<RenewalData>("/renewals/dashboard", {
    refreshInterval: 60000,
    onError: () => {
      /* ignore renewal errors silently */
    },
  });

  if (isLoading)
    return (
      <PageLayout title="Chargement...">
        <LoadingState text="Chargement du dashboard..." />
      </PageLayout>
    );
  if (error || !data)
    return (
      <PageLayout title="Erreur">
        <ErrorState message={error?.message ?? "Erreur"} onRetry={() => mutate()} />
      </PageLayout>
    );

  const { financial, aging, payers, operational, commercial, marketing, cosium } = data;

  return (
    <PageLayout title="Dashboard" description="Tableau de pilotage OptiFlow" breadcrumb={[{ label: "Dashboard" }]}>
      <div className="flex items-center gap-2 mb-6">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              period === p.key
                ? "bg-primary text-white"
                : "bg-bg-card text-text-secondary border border-border hover:bg-gray-100"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
      <DashboardKPIs financial={financial} />
      <DashboardCharts caParMois={commercial.ca_par_mois} aging={aging} />
      <CosiumDataSection cosium={cosium} />
      <DashboardSections operational={operational} commercial={commercial} marketing={marketing} />
      <RenewalSection renewalData={renewalData} />
      <PayersTable payers={payers.payers} />
    </PageLayout>
  );
}
