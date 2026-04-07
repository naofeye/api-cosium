"use client";

import { useState, useMemo, useCallback } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import dynamic from "next/dynamic";
import { DashboardKPIs } from "./components/DashboardKPIs";
import { DashboardSections } from "./components/DashboardSections";
import { RenewalSection } from "./components/RenewalSection";
import { PayersTable } from "./components/PayersTable";
import { RecentActivity } from "./components/RecentActivity";
import { OnboardingGuide } from "@/components/ui/OnboardingGuide";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { SkeletonCard } from "@/components/ui/SkeletonCard";

const DashboardCharts = dynamic(() => import("./components/DashboardCharts").then((m) => ({ default: m.DashboardCharts })), {
  ssr: false,
  loading: () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <SkeletonCard />
      <SkeletonCard />
    </div>
  ),
});
import { useToast } from "@/components/ui/Toast";
import { FileDown, Calendar, Eye, RefreshCw as RefreshIcon, Clock, ClipboardCheck, Search, AlertCircle, Settings, Users, FileSearch } from "lucide-react";
import Link from "next/link";
import { formatMoney } from "@/lib/format";

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
  comparison: {
    ca_total_delta: number | null;
    montant_encaisse_delta: number | null;
    reste_a_encaisser_delta: number | null;
    taux_recouvrement_delta: number | null;
    clients_delta: number | null;
    factures_delta: number | null;
  } | null;
}

interface RenewalData {
  total_opportunities: number;
  high_score_count: number;
  estimated_revenue: number;
}

interface OverdueInvoice {
  id: number;
  customer_name: string;
  montant_ttc: number;
  date_emission: string;
  days_overdue: number;
}

interface OverdueInvoicesResponse {
  items: OverdueInvoice[];
  total: number;
}

interface DataQualityData {
  extractions?: {
    total_documents: number;
    total_extracted: number;
    extraction_rate: number;
    by_type: Record<string, number>;
  } | null;
}

interface CalendarEvent {
  id: number | string;
  start_date: string;
  end_date?: string;
  customer_fullname: string;
  category_name: string;
  category_color: string;
}

interface CalendarEventsResponse {
  events: CalendarEvent[];
  total: number;
}

function formatTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "--:--";
  }
}

function formatRelativeTime(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 10) return "a l'instant";
  if (seconds < 60) return `il y a ${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `il y a ${minutes}min`;
  const hours = Math.floor(minutes / 60);
  return `il y a ${hours}h`;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export default function DashboardPage() {
  const [period, setPeriod] = useState<PeriodKey>("all");
  const [exporting, setExporting] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const { toast } = useToast();
  const { date_from, date_to } = useMemo(() => getDateRange(period), [period]);

  // Today's date for calendar events
  const todayStr = useMemo(() => formatDate(new Date()), []);
  const { data: calendarData } = useSWR<CalendarEventsResponse>(
    `/cosium/calendar-events?date_from=${todayStr}&date_to=${todayStr}&page_size=10`,
    {
      refreshInterval: 120000,
      onError: () => { /* ignore calendar errors silently */ },
    },
  );
  const todayEvents = calendarData?.events ?? [];

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
    {
      refreshInterval: 60000,
      onSuccess: () => setLastUpdated(new Date()),
    },
  );
  const { data: renewalData } = useSWR<RenewalData>("/renewals/dashboard", {
    refreshInterval: 60000,
    onError: () => {
      /* ignore renewal errors silently */
    },
  });

  const { data: dataQuality } = useSWR<DataQualityData>(
    "/admin/data-quality",
    {
      refreshInterval: 300000,
      onError: () => { /* ignore data quality errors silently */ },
    },
  );

  const { data: overdueData } = useSWR<OverdueInvoicesResponse>(
    "/cosium-invoices?status=impayee&page_size=5",
    {
      refreshInterval: 120000,
      onError: () => { /* ignore overdue errors silently */ },
    },
  );
  const overdueInvoices = overdueData?.items ?? [];

  if (isLoading)
    return (
      <PageLayout title="Dashboard" description="Tableau de pilotage OptiFlow" breadcrumb={[{ label: "Dashboard" }]}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </PageLayout>
    );
  if (error || !data)
    return (
      <PageLayout title="Erreur">
        <ErrorState message={error?.message ?? "Erreur"} onRetry={() => mutate()} />
      </PageLayout>
    );

  const { financial, aging, payers, operational, commercial, marketing, cosium, cosium_counts, cosium_ca_par_mois, comparison } =
    data;

  return (
    <PageLayout title="Dashboard" description="Tableau de pilotage OptiFlow" breadcrumb={[{ label: "Dashboard" }]}>
      <OnboardingGuide />

      {/* Today's appointments */}
      <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
            Rendez-vous du jour
          </h3>
        </div>
        {todayEvents.length === 0 ? (
          <p className="text-sm text-text-secondary">Aucun rendez-vous aujourd&apos;hui</p>
        ) : (
          <div className="space-y-2">
            {todayEvents.map((ev) => (
              <div key={ev.id} className="flex items-center gap-3 text-sm">
                <span className="w-12 font-mono text-text-secondary">{formatTime(ev.start_date)}</span>
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: ev.category_color || "#6b7280" }}
                />
                <span className="font-medium text-text-primary">{ev.customer_fullname}</span>
                <span className="text-text-secondary">{ev.category_name}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Period selector + actions */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            aria-pressed={period === p.key}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
              period === p.key
                ? "bg-primary text-white"
                : "bg-bg-card text-text-secondary border border-border hover:bg-gray-100"
            }`}
          >
            {p.label}
          </button>
        ))}
        {lastUpdated && (
          <span className="text-xs text-text-secondary ml-2">
            Mis a jour {formatRelativeTime(lastUpdated)}
          </span>
        )}
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
        <DashboardKPIs financial={financial} cosiumCounts={cosium_counts} cosium={cosium} comparison={comparison} />
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

      {/* Intelligence documentaire */}
      {dataQuality?.extractions && dataQuality.extractions.total_extracted > 0 && (
        <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileSearch className="h-4 w-4 text-primary" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
                Intelligence documentaire
              </h3>
            </div>
            <Link
              href="/admin/data-quality"
              className="text-xs font-medium text-primary hover:underline"
            >
              Voir le detail &rarr;
            </Link>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
            <span className="font-semibold text-text-primary tabular-nums">
              {dataQuality.extractions.total_extracted.toLocaleString("fr-FR")} documents analyses
            </span>
            <span className="text-text-secondary">
              {Object.entries(dataQuality.extractions.by_type)
                .map(([type, count]) => {
                  const labels: Record<string, string> = {
                    ordonnance: "ordonnances",
                    devis: "devis",
                    attestation_mutuelle: "attestations",
                    facture: "factures",
                    courrier: "courriers",
                    autre: "autres",
                  };
                  return `${count.toLocaleString("fr-FR")} ${labels[type] || type}`;
                })
                .join(" | ")}
            </span>
          </div>
          <div className="mt-2">
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${Math.min(dataQuality.extractions.extraction_rate, 100)}%` }}
                />
              </div>
              <span className="text-xs text-text-secondary tabular-nums">
                {dataQuality.extractions.extraction_rate}% extraits
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Actions rapides */}
      <div className="mb-8">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-3">
          Actions rapides
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link
            href="/pec-dashboard"
            className="flex flex-col items-center gap-2 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary hover:shadow-md transition-all text-center"
          >
            <ClipboardCheck className="h-6 w-6 text-primary" aria-hidden="true" />
            <span className="text-sm font-semibold text-text-primary">Nouvelle PEC</span>
            <span className="text-xs text-text-secondary">Preparer une prise en charge</span>
          </Link>
          <button
            onClick={() => {
              // Trigger Ctrl+K search
              const event = new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true });
              document.dispatchEvent(event);
            }}
            className="flex flex-col items-center gap-2 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary hover:shadow-md transition-all text-center"
          >
            <Search className="h-6 w-6 text-primary" aria-hidden="true" />
            <span className="text-sm font-semibold text-text-primary">Rechercher un client</span>
            <span className="text-xs text-text-secondary">Ctrl+K pour la recherche</span>
          </button>
          <Link
            href="/cosium-factures?status=impayee"
            className="flex flex-col items-center gap-2 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary hover:shadow-md transition-all text-center"
          >
            <AlertCircle className="h-6 w-6 text-danger" aria-hidden="true" />
            <span className="text-sm font-semibold text-text-primary">Voir les impayes</span>
            <span className="text-xs text-text-secondary">Factures en attente de paiement</span>
          </Link>
          <Link
            href="/admin"
            className="flex flex-col items-center gap-2 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary hover:shadow-md transition-all text-center"
          >
            <Settings className="h-6 w-6 text-primary" aria-hidden="true" />
            <span className="text-sm font-semibold text-text-primary">Sync Cosium</span>
            <span className="text-xs text-text-secondary">Synchroniser les donnees</span>
          </Link>
        </div>
      </div>

      {/* Clients a relancer (impayes > 30j) */}
      {overdueInvoices.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card p-4 mb-8 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-danger" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
                Clients a relancer
              </h3>
            </div>
            <Link
              href="/relances"
              className="text-xs font-medium text-primary hover:underline"
            >
              Voir toutes les relances &rarr;
            </Link>
          </div>
          <div className="space-y-2">
            {overdueInvoices.map((inv) => {
              const colorClass = inv.days_overdue > 60
                ? "text-danger"
                : inv.days_overdue > 30
                  ? "text-amber-600"
                  : "text-text-secondary";
              return (
                <div key={inv.id} className="flex items-center justify-between text-sm rounded-lg px-3 py-2 hover:bg-gray-50">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="font-medium text-text-primary truncate">{inv.customer_name}</span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <span className="font-semibold tabular-nums">{formatMoney(inv.montant_ttc)}</span>
                    <span className={`text-xs font-medium ${colorClass}`}>
                      {inv.days_overdue}j de retard
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

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

      {/* Derniere activite */}
      <div className="mb-8">
        <ErrorBoundary name="RecentActivity">
          <RecentActivity />
        </ErrorBoundary>
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
