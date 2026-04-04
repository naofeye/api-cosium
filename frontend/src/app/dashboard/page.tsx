"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatMoney } from "@/lib/format";
import { FolderOpen, ShoppingCart, Megaphone, RefreshCw } from "lucide-react";
import Link from "next/link";
import { DashboardKPIs } from "./components/DashboardKPIs";
import { DashboardCharts } from "./components/DashboardCharts";

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

  const { financial, aging, payers, operational, commercial, marketing } = data;

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Operationnel */}
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <FolderOpen className="h-5 w-5" /> Operationnel
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Dossiers en cours</span>
              <span className="font-semibold">{operational.dossiers_en_cours}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Dossiers complets</span>
              <span className="font-semibold text-emerald-700">{operational.dossiers_complets}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Taux completude</span>
              <span
                className={`font-semibold ${operational.taux_completude > 80 ? "text-emerald-700" : "text-amber-700"}`}
              >
                {operational.taux_completude}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Pieces manquantes</span>
              <span
                className={`font-semibold ${operational.pieces_manquantes > 0 ? "text-red-700" : "text-emerald-700"}`}
              >
                {operational.pieces_manquantes}
              </span>
            </div>
          </div>
        </div>

        {/* Commercial */}
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" /> Commercial
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Devis en cours</span>
              <span className="font-semibold">{commercial.devis_en_cours}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Devis signes</span>
              <span className="font-semibold text-emerald-700">{commercial.devis_signes}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Taux conversion</span>
              <span
                className={`font-semibold ${commercial.taux_conversion > 50 ? "text-emerald-700" : "text-amber-700"}`}
              >
                {commercial.taux_conversion}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Panier moyen</span>
              <span className="font-semibold">{formatMoney(commercial.panier_moyen)}</span>
            </div>
          </div>
        </div>

        {/* Marketing */}
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Megaphone className="h-5 w-5" /> Marketing
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Campagnes total</span>
              <span className="font-semibold">{marketing.campagnes_total}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Campagnes envoyees</span>
              <span className="font-semibold text-emerald-700">{marketing.campagnes_envoyees}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Messages envoyes</span>
              <span className="font-semibold">{marketing.messages_envoyes}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Renouvellements du mois */}
      {renewalData && renewalData.total_opportunities > 0 && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <RefreshCw className="h-5 w-5" /> Renouvellements du mois
            </h3>
            <Link href="/renewals" className="text-sm text-primary hover:underline">
              Voir tout →
            </Link>
          </div>
          <div className="grid grid-cols-3 gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-primary tabular-nums">{renewalData.total_opportunities}</p>
              <p className="text-sm text-text-secondary mt-1">Opportunites</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-success tabular-nums">{renewalData.high_score_count}</p>
              <p className="text-sm text-text-secondary mt-1">Fort potentiel</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-warning tabular-nums">
                {formatMoney(renewalData.estimated_revenue)}
              </p>
              <p className="text-sm text-text-secondary mt-1">CA potentiel</p>
            </div>
          </div>
        </div>
      )}

      {/* Performance mutuelles */}
      {payers.payers.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Performance organismes payeurs</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 text-left font-medium text-text-secondary">Organisme</th>
                <th className="pb-2 text-left font-medium text-text-secondary">Type</th>
                <th className="pb-2 text-right font-medium text-text-secondary">Demande</th>
                <th className="pb-2 text-right font-medium text-text-secondary">Accorde</th>
                <th className="pb-2 text-center font-medium text-text-secondary">Taux acceptation</th>
              </tr>
            </thead>
            <tbody>
              {payers.payers.map((p, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  <td className="py-2 font-medium">{p.name}</td>
                  <td className="py-2">
                    <StatusBadge status={p.type} />
                  </td>
                  <td className="py-2 text-right tabular-nums">{formatMoney(p.total_requested)}</td>
                  <td className="py-2 text-right tabular-nums">{formatMoney(p.total_accepted)}</td>
                  <td className="py-2 text-center">
                    <span
                      className={`font-semibold ${p.acceptance_rate > 80 ? "text-emerald-700" : p.acceptance_rate > 50 ? "text-amber-700" : "text-red-700"}`}
                    >
                      {p.acceptance_rate}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageLayout>
  );
}
