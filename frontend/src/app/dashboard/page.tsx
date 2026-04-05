"use client";

import { useState, useMemo, useCallback } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { DashboardKPIs } from "./components/DashboardKPIs";
import { DashboardCharts } from "./components/DashboardCharts";
import { DashboardSections } from "./components/DashboardSections";
import { RenewalSection } from "./components/RenewalSection";
import { PayersTable } from "./components/PayersTable";
import { OnboardingGuide } from "@/components/ui/OnboardingGuide";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useToast } from "@/components/ui/Toast";
import { FileDown, Calendar, Eye, RefreshCw as RefreshIcon } from "lucide-react";
import Link from "next/link";

type PeriodKey = "today" | "7d" | "30d" | "90d" | "all";

const PERIODS: { key: PeriodKey; label: string; days: number }[] = [
  { key: "today", label: "Aujourd'hui", days: 0 },
  { key: "7d", label: "7 jours", days: 7 },
  { key: "30d", label: "30 jours", days: 30 },
  { key: "90d", label: "90 jours", days: 90 },
  { key: "all", label: "Tout", days: -1 },
];

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function getDateRange(period: PeriodKey): { date_from: string; date_to: string } {
  const now = new Date();
  const date_to = formatDate(now);
  if (period === "all") {
    return { date_from: "", date_to: "" };
  }
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
    payers: {
      name: string;
      type: string;
      acceptance_rate: number;
      total_requested: number;
      total_accepted: number;
    }[];
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
  cosium_counts: {
    total_clients: number;
    total_rdv: number;
    total_prescriptions: number;
    total_payments: number;
  } | null;
  cosium_ca_par_mois: { mois: string; ca: number }[];
}

interface RenewalData {
  total_opportunities: number;
  high_score_count: number;
  estimated_revenue: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export default function DashboardPage() {
  const [period, setPeriod] = useState<PeriodKey>("all");
  const [exporting, setExporting] = useState(false);
  const { toast } = useToast();
  const { date_from, date_to } = useMemo(() => getDateRange(period), [period]);

  const handleExportPDF = useCallback(async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (date_from) params.set("date_from", date_from);
      if (date_to) params.set("date_to", date_to);
      const resp = await fetch(`${API_BASE}/exports/dashboard-pdf?${params.toString()}`, {
        credentials: "include",
      });
      if (!resp.ok) throw new Error("Erreur lors de l'export");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dashboard_optiflow_${date_from || "all"}_${date_to || "all"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast("Impossible de telecharger le PDF. Reessayez.", "error");
    } finally {
      setExporting(false);
    }
  }, [date_from, date_to, toast]);

  const queryParams = date_from
    ? `?date_from=${date_from}&date_to=${date_to}`
    : "";

  const { data, error, isLoading, mutate } = useSWR<DashboardData>(
    `/analytics/dashboard${queryParams}`,
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

  const { financial, aging, payers, operational, commercial, marketing, cosium, cosium_counts, cosium_ca_par_mois } =
    data;

  return (
    <PageLayout title="Dashboard" description="Tableau de pilotage OptiFlow" breadcrumb={[{ label: "Dashboard" }]}>
      <OnboardingGuide />

      {/* Period selector + actions */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
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
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleExportPDF}
            disabled={exporting}
            className="inline-flex items-center gap-2 rounded-lg bg-bg-card border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-100 transition-colors disabled:opacity-50"
            title="Exporter le dashboard en PDF"
            aria-label="Exporter le dashboard en PDF"
          >
            <FileDown className="h-4 w-4" aria-hidden="true" />
            {exporting ? "Export en cours..." : "Exporter PDF"}
          </button>
        </div>
      </div>

      {/* Main KPIs (financial + volume) */}
      <ErrorBoundary name="DashboardKPIs">
        <DashboardKPIs financial={financial} cosiumCounts={cosium_counts} cosium={cosium} />
      </ErrorBoundary>

      {/* Charts: CA par mois + document distribution */}
      <ErrorBoundary name="DashboardCharts">
        <DashboardCharts
          caParMois={commercial.ca_par_mois}
          cosiumCaParMois={cosium_ca_par_mois || []}
          aging={aging}
          cosium={cosium}
        />
      </ErrorBoundary>

      {/* Quick links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Link
          href="/agenda"
          className="flex items-center gap-3 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary transition-colors"
        >
          <Calendar className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-semibold text-text-primary">Agenda</p>
            <p className="text-xs text-text-secondary">
              {cosium_counts ? `${cosium_counts.total_rdv.toLocaleString("fr-FR")} rendez-vous` : "Voir le planning"}
            </p>
          </div>
        </Link>
        <Link
          href="/ordonnances"
          className="flex items-center gap-3 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary transition-colors"
        >
          <Eye className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-semibold text-text-primary">Ordonnances</p>
            <p className="text-xs text-text-secondary">
              {cosium_counts
                ? `${cosium_counts.total_prescriptions.toLocaleString("fr-FR")} prescriptions`
                : "Voir les ordonnances"}
            </p>
          </div>
        </Link>
        <Link
          href="/cosium-factures"
          className="flex items-center gap-3 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary transition-colors"
        >
          <RefreshIcon className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-semibold text-text-primary">Facturation Cosium</p>
            <p className="text-xs text-text-secondary">
              {cosium
                ? `${(cosium.invoice_count + cosium.quote_count + cosium.credit_note_count).toLocaleString("fr-FR")} documents`
                : "Voir les factures"}
            </p>
          </div>
        </Link>
      </div>

      {/* Operational / Commercial / Marketing */}
      <ErrorBoundary name="DashboardSections">
        <DashboardSections operational={operational} commercial={commercial} marketing={marketing} />
      </ErrorBoundary>

      {/* Renewals */}
      <ErrorBoundary name="RenewalSection">
        <RenewalSection renewalData={renewalData} />
      </ErrorBoundary>

      {/* Payers performance */}
      <ErrorBoundary name="PayersTable">
        <PayersTable payers={payers.payers} />
      </ErrorBoundary>
    </PageLayout>
  );
}
