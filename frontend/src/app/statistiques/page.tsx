"use client";

import { useState, useMemo, useCallback } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { KPICard } from "@/components/ui/KPICard";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { useToast } from "@/components/ui/Toast";
import { formatMoney } from "@/lib/format";
import {
  Euro,
  CheckCircle,
  Clock,
  TrendingUp,
  FileText,
  FileDown,
  ShoppingCart,
  FolderOpen,
  Target,
} from "lucide-react";
import { API_BASE } from "@/lib/api";

const StatistiquesCharts = dynamic(
  () => import("./components/StatistiquesCharts").then((m) => ({ default: m.StatistiquesCharts })),
  {
    ssr: false,
    loading: () => (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    ),
  },
);

type PeriodKey = "7d" | "30d" | "90d" | "365d";

const PERIODS: { key: PeriodKey; label: string; days: number }[] = [
  { key: "7d", label: "7 jours", days: 7 },
  { key: "30d", label: "30 jours", days: 30 },
  { key: "90d", label: "90 jours", days: 90 },
  { key: "365d", label: "1 an", days: 365 },
];

function fmtDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function getRange(period: PeriodKey): { date_from: string; date_to: string } {
  const now = new Date();
  const date_to = fmtDate(now);
  const days = PERIODS.find((p) => p.key === period)!.days;
  const from = new Date(now);
  from.setDate(from.getDate() - days);
  return { date_from: fmtDate(from), date_to };
}

interface DashboardData {
  financial: {
    ca_total: number;
    montant_facture: number;
    montant_encaisse: number;
    reste_a_encaisser: number;
    taux_recouvrement: number;
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
  cosium: {
    total_facture_cosium: number;
    total_outstanding: number;
    total_paid: number;
    invoice_count: number;
    quote_count: number;
    credit_note_count: number;
  } | null;
}

export default function StatistiquesPage() {
  const [period, setPeriod] = useState<PeriodKey>("30d");
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingXlsx, setExportingXlsx] = useState(false);
  const [exportingMonthly, setExportingMonthly] = useState(false);
  const { toast } = useToast();
  const { date_from, date_to } = useMemo(() => getRange(period), [period]);

  const { data, error, isLoading, mutate } = useSWR<DashboardData>(
    `/analytics/dashboard?date_from=${date_from}&date_to=${date_to}`,
    { refreshInterval: 60000 },
  );

  const downloadFile = useCallback(
    async (endpoint: string, filename: string, setLoading: (v: boolean) => void) => {
      setLoading(true);
      try {
        const resp = await fetch(`${API_BASE}${endpoint}`, { credentials: "include" });
        if (!resp.ok) throw new Error("Erreur export");
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      } catch {
        toast("Impossible de telecharger le fichier. Reessayez.", "error");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const handleExport = useCallback(
    async (format: "pdf" | "xlsx") => {
      const setLoading = format === "pdf" ? setExportingPdf : setExportingXlsx;
      const endpoint =
        format === "pdf"
          ? `/exports/dashboard-pdf?date_from=${date_from}&date_to=${date_to}`
          : `/exports/balance-clients?date_from=${date_from}&date_to=${date_to}`;
      const filename = format === "pdf" ? `statistiques_${date_from}.pdf` : `balance_clients_${date_from}.xlsx`;
      await downloadFile(endpoint, filename, setLoading);
    },
    [date_from, date_to, downloadFile],
  );

  const handleMonthlyReport = useCallback(async () => {
    const now = new Date();
    const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const monthStr = `${prevMonth.getFullYear()}-${String(prevMonth.getMonth() + 1).padStart(2, "0")}`;
    await downloadFile(
      `/exports/monthly-report?month=${monthStr}`,
      `rapport_mensuel_${monthStr}.pdf`,
      setExportingMonthly,
    );
  }, [downloadFile]);

  if (isLoading)
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Statistiques" }]}>
        <LoadingState text="Chargement des statistiques..." />
      </PageLayout>
    );
  if (error || !data)
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Statistiques" }]}>
        <ErrorState message={error?.message ?? "Erreur"} onRetry={() => mutate()} />
      </PageLayout>
    );

  const { financial, operational, commercial, cosium } = data;

  return (
    <PageLayout
      title="Statistiques"
      description="Analyse detaillee de l'activite"
      breadcrumb={[{ label: "Statistiques" }]}
    >
      {/* Period selector + export buttons */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
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
        <div className="ml-auto flex gap-2">
          <button
            onClick={handleMonthlyReport}
            disabled={exportingMonthly}
            className="inline-flex items-center gap-2 rounded-lg bg-primary text-white px-3 py-1.5 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            title="Telecharger le rapport mensuel (mois precedent)"
            aria-label="Rapport mensuel"
          >
            <FileDown className="h-4 w-4" aria-hidden="true" />
            {exportingMonthly ? "Generation..." : "Rapport mensuel"}
          </button>
          <button
            onClick={() => handleExport("pdf")}
            disabled={exportingPdf}
            className="inline-flex items-center gap-2 rounded-lg bg-bg-card border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-100 transition-colors disabled:opacity-50"
            title="Exporter en PDF"
            aria-label="Exporter en PDF"
          >
            <FileDown className="h-4 w-4" aria-hidden="true" />
            {exportingPdf ? "Export..." : "PDF"}
          </button>
          <button
            onClick={() => handleExport("xlsx")}
            disabled={exportingXlsx}
            className="inline-flex items-center gap-2 rounded-lg bg-bg-card border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-100 transition-colors disabled:opacity-50"
            title="Exporter la balance clients (Excel)"
            aria-label="Exporter la balance clients (Excel)"
          >
            <FileDown className="h-4 w-4" aria-hidden="true" />
            {exportingXlsx ? "Export..." : "Balance Excel"}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard icon={Euro} label="CA Total" value={formatMoney(financial.ca_total)} color="primary" />
        <KPICard icon={CheckCircle} label="Encaisse" value={formatMoney(financial.montant_encaisse)} color="success" />
        <KPICard
          icon={Clock}
          label="Reste a encaisser"
          value={formatMoney(financial.reste_a_encaisser)}
          color={financial.reste_a_encaisser > 0 ? "danger" : "success"}
        />
        <KPICard
          icon={TrendingUp}
          label="Taux recouvrement"
          value={`${financial.taux_recouvrement} %`}
          color={financial.taux_recouvrement > 80 ? "success" : "warning"}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard icon={FolderOpen} label="Dossiers en cours" value={String(operational.dossiers_en_cours)} color="info" />
        <KPICard icon={Target} label="Completude" value={`${operational.taux_completude} %`} color={operational.taux_completude > 80 ? "success" : "warning"} />
        <KPICard icon={ShoppingCart} label="Panier moyen" value={formatMoney(commercial.panier_moyen)} color="primary" />
        <KPICard icon={FileText} label="Taux conversion" value={`${commercial.taux_conversion} %`} color={commercial.taux_conversion > 50 ? "success" : "warning"} />
      </div>

      {/* Charts (lazy loaded) */}
      <StatistiquesCharts caParMois={commercial.ca_par_mois} cosium={cosium} />

      {/* Cosium summary if available */}
      {cosium && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-8">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Resume Cosium</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-text-primary">{cosium.invoice_count}</p>
              <p className="text-sm text-text-secondary">Factures</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-text-primary">{cosium.quote_count}</p>
              <p className="text-sm text-text-secondary">Devis</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-text-primary">{cosium.credit_note_count}</p>
              <p className="text-sm text-text-secondary">Avoirs</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{formatMoney(cosium.total_facture_cosium)}</p>
              <p className="text-sm text-text-secondary">Total facture</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-600">{formatMoney(cosium.total_paid)}</p>
              <p className="text-sm text-text-secondary">Paye</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{formatMoney(cosium.total_outstanding)}</p>
              <p className="text-sm text-text-secondary">Impaye</p>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
