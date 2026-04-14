"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { logger } from "@/lib/logger";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import {
  FolderOpen,
  FileText,
  AlertTriangle,
  Euro,
  CheckCircle,
  Clock,
  RefreshCw,
  ArrowRight,
  AlertCircle,
  X,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

interface DashboardData {
  cases_count: number;
  documents_count: number;
  alerts_count: number;
  payments_due: number;
  payments_paid: number;
  payments_remaining: number;
}

interface ActionItem {
  id: number;
  type: string;
  title: string;
  description: string | null;
  entity_type: string;
  entity_id: number;
  priority: string;
  status: string;
  created_at: string;
}

interface ActionItemList {
  items: ActionItem[];
  total: number;
  counts: Record<string, number>;
}

const TYPE_LABELS: Record<string, string> = {
  dossier_incomplet: "Dossiers incomplets",
  paiement_retard: "Paiements en attente",
  pec_attente: "PEC en attente",
  relance_faire: "Relances a faire",
  devis_expiration: "Devis expirant",
  impaye_cosium: "Impayes Cosium",
  devis_dormant: "Devis dormants",
  rdv_demain: "RDV demain",
  renouvellement: "Renouvellements eligibles",
};

const TYPE_ICONS: Record<string, typeof FolderOpen> = {
  dossier_incomplet: FolderOpen,
  paiement_retard: Euro,
  pec_attente: Clock,
  relance_faire: AlertTriangle,
  devis_expiration: FileText,
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-200",
  high: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  medium: "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200",
  low: "bg-gray-50 text-gray-600 ring-1 ring-inset ring-gray-200",
};

const PRIORITY_LABELS: Record<string, string> = {
  critical: "Critique",
  high: "Haute",
  medium: "Moyenne",
  low: "Basse",
};

export default function ActionsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const typeFilter = searchParams.get("type");
  const {
    data: dashboard,
    error: dashErr,
    isLoading: dashLoading,
    mutate: mutateDash,
  } = useSWR<DashboardData>("/dashboard/summary", { refreshInterval: 30000 });
  const {
    data: actions,
    error: actErr,
    isLoading: actLoading,
    mutate: mutateActions,
  } = useSWR<ActionItemList>("/action-items?status=pending", { refreshInterval: 30000 });
  const [refreshing, setRefreshing] = useState(false);
  const [onboardingDismissed, setOnboardingDismissed] = useState(true);

  useEffect(() => {
    const dismissed = localStorage.getItem("optiflow_onboarding_dismissed");
    setOnboardingDismissed(dismissed === "true");
  }, []);

  const dismissOnboarding = () => {
    localStorage.setItem("optiflow_onboarding_dismissed", "true");
    setOnboardingDismissed(true);
  };

  const showOnboarding =
    !onboardingDismissed &&
    dashboard &&
    dashboard.cases_count === 0;

  const isLoading = dashLoading || actLoading;
  const error = dashErr?.message ?? actErr?.message ?? null;

  const refresh = () => {
    setRefreshing(true);
    fetchJson<ActionItemList>("/action-items/refresh", { method: "POST" })
      .then(() => mutateActions())
      .catch((err) => {
        logger.error("[Actions] Erreur lors de l'actualisation:", err);
      })
      .finally(() => setRefreshing(false));
  };

  const markDone = (itemId: number) => {
    fetchJson(`/action-items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "done" }),
    })
      .then(() => mutateActions())
      .catch((err) => {
        logger.error("[Actions] Erreur lors du marquage:", err);
      });
  };

  const dismiss = (itemId: number) => {
    fetchJson(`/action-items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "dismissed" }),
    })
      .then(() => mutateActions())
      .catch((err) => {
        logger.error("[Actions] Erreur lors du report:", err);
      });
  };

  const getEntityLink = (item: ActionItem): string => {
    if (item.entity_type === "case") return `/cases/${item.entity_id}`;
    if (item.entity_type === "payment") return `/cases`;
    return "#";
  };

  if (isLoading) {
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Actions" }]}>
        <LoadingState text="Chargement de vos priorites..." />
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Actions" }]}>
        <ErrorState
          message={error}
          onRetry={() => {
            mutateDash();
            mutateActions();
          }}
        />
      </PageLayout>
    );
  }

  if (!dashboard || !actions) return null;

  const filteredItems = typeFilter ? actions.items.filter((i) => i.type === typeFilter) : actions.items;
  const groupedActions: Record<string, ActionItem[]> = {};
  for (const item of filteredItems) {
    if (!groupedActions[item.type]) groupedActions[item.type] = [];
    groupedActions[item.type].push(item);
  }

  return (
    <PageLayout
      title=""
      breadcrumb={[{ label: "Actions" }]}
      actions={
        <Button variant="outline" onClick={refresh} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Actualisation..." : "Actualiser"}
        </Button>
      }
    >
      {/* Greeting section */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">
          {(() => {
            const hour = new Date().getHours();
            if (hour < 12) return "Bonjour";
            if (hour < 18) return "Bon apres-midi";
            return "Bonsoir";
          })()}, bienvenue sur OptiFlow
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Voici vos priorites du jour — {new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </p>
        {typeFilter && (
          <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-blue-50 border border-blue-200 px-3 py-1.5 text-sm text-blue-800">
            <span className="font-medium">Filtre :</span>
            <span>{TYPE_LABELS[typeFilter] ?? typeFilter}</span>
            <span className="rounded-full bg-blue-200 px-2 py-0.5 text-xs font-bold tabular-nums">{filteredItems.length}</span>
            <Link href="/actions" className="ml-1 hover:bg-blue-200 rounded-full p-0.5" aria-label="Retirer le filtre">
              <X className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}
      </div>
      {showOnboarding && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
          <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" aria-label="Bienvenue" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-blue-900">Bienvenue sur OptiFlow AI !</p>
            <p className="mt-1 text-sm text-blue-800">
              Commencez par synchroniser vos donnees Cosium ou{" "}
              <Link href="/cases/new" className="font-medium underline hover:text-blue-900">
                creer votre premier dossier client
              </Link>.
            </p>
          </div>
          <button
            onClick={dismissOnboarding}
            className="shrink-0 rounded-lg p-1 text-blue-400 hover:bg-blue-100 hover:text-blue-600 transition-colors"
            aria-label="Fermer le message de bienvenue"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <KPICard icon={FolderOpen} label="Dossiers actifs" value={dashboard.cases_count} color="primary" />
        <KPICard icon={FileText} label="Documents" value={dashboard.documents_count} color="info" />
        <KPICard
          icon={AlertTriangle}
          label="Actions en cours"
          value={actions.total}
          color={actions.total > 0 ? "danger" : "success"}
        />
        <KPICard icon={Euro} label="Total facture" value={formatMoney(dashboard.payments_due)} color="primary" />
        <KPICard icon={CheckCircle} label="Encaisse" value={formatMoney(dashboard.payments_paid)} color="success" />
        <KPICard
          icon={Clock}
          label="Reste du"
          value={formatMoney(dashboard.payments_remaining)}
          color={dashboard.payments_remaining > 0 ? "danger" : "success"}
        />
      </div>

      <h2 className="text-lg font-semibold text-text-primary mb-4">File d&apos;actions ({actions.total})</h2>

      {actions.items.length === 0 ? (
        <EmptyState
          title="Tout est a jour !"
          description="Aucune action urgente pour le moment. Bravo !"
          action={
            <Link href="/cases/new">
              <Button>Nouveau dossier</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedActions).map(([type, items]) => {
            const Icon = TYPE_ICONS[type] || AlertCircle;
            return (
              <div key={type} className="rounded-xl border border-border bg-bg-card shadow-sm hover:shadow-md transition-shadow duration-200">
                <div className="flex items-center gap-3 border-b border-border px-5 py-3.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/20">
                    <Icon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  </div>
                  <h3 className="text-sm font-semibold text-text-primary">{TYPE_LABELS[type] || type}</h3>
                  <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:ring-blue-800">
                    {items.length}
                  </span>
                </div>
                <div className="divide-y divide-border">
                  {items.map((item) => (
                    <div key={item.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/80 dark:hover:bg-gray-800/50 transition-colors duration-150">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-text-primary">{item.title}</p>
                        {item.description && <p className="text-xs text-text-secondary mt-0.5">{item.description}</p>}
                      </div>
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.medium}`}
                      >
                        {PRIORITY_LABELS[item.priority] || item.priority}
                      </span>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <button
                          onClick={() => markDone(item.id)}
                          className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-50 transition-colors"
                          title="Marquer comme traite"
                        >
                          Traite
                        </button>
                        <button
                          onClick={() => dismiss(item.id)}
                          className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-gray-100 transition-colors"
                          title="Reporter"
                        >
                          Reporter
                        </button>
                        <button
                          onClick={() => router.push(getEntityLink(item))}
                          className="rounded-lg p-1.5 text-primary hover:bg-blue-50 transition-colors"
                          aria-label="Voir le detail"
                        >
                          <ArrowRight className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}
