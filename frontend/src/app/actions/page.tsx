"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
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
};

const TYPE_ICONS: Record<string, typeof FolderOpen> = {
  dossier_incomplet: FolderOpen,
  paiement_retard: Euro,
  pec_attente: Clock,
  relance_faire: AlertTriangle,
  devis_expiration: FileText,
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-amber-100 text-amber-800",
  medium: "bg-blue-100 text-blue-800",
  low: "bg-gray-100 text-gray-600",
};

const PRIORITY_LABELS: Record<string, string> = {
  critical: "Critique",
  high: "Haute",
  medium: "Moyenne",
  low: "Basse",
};

export default function ActionsPage() {
  const router = useRouter();
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

  const isLoading = dashLoading || actLoading;
  const error = dashErr?.message ?? actErr?.message ?? null;

  const refresh = () => {
    setRefreshing(true);
    fetchJson<ActionItemList>("/action-items/refresh", { method: "POST" })
      .then(() => mutateActions())
      .catch(() => {})
      .finally(() => setRefreshing(false));
  };

  const markDone = (itemId: number) => {
    fetchJson(`/action-items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "done" }),
    })
      .then(() => mutateActions())
      .catch(() => {});
  };

  const dismiss = (itemId: number) => {
    fetchJson(`/action-items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "dismissed" }),
    })
      .then(() => mutateActions())
      .catch(() => {});
  };

  const getEntityLink = (item: ActionItem): string => {
    if (item.entity_type === "case") return `/cases/${item.entity_id}`;
    if (item.entity_type === "payment") return `/cases`;
    return "#";
  };

  if (isLoading) {
    return (
      <PageLayout title="Chargement...">
        <LoadingState text="Chargement de vos priorites..." />
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout title="Erreur">
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

  const groupedActions: Record<string, ActionItem[]> = {};
  for (const item of actions.items) {
    if (!groupedActions[item.type]) groupedActions[item.type] = [];
    groupedActions[item.type].push(item);
  }

  return (
    <PageLayout
      title="Bonjour, bienvenue sur OptiFlow AI"
      description="Voici vos priorites du jour"
      breadcrumb={[{ label: "Actions" }]}
      actions={
        <Button variant="outline" onClick={refresh} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Actualisation..." : "Actualiser"}
        </Button>
      }
    >
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
              <div key={type} className="rounded-xl border border-border bg-bg-card shadow-sm">
                <div className="flex items-center gap-3 border-b border-border px-5 py-3">
                  <Icon className="h-5 w-5 text-text-secondary" />
                  <h3 className="text-sm font-semibold text-text-primary">{TYPE_LABELS[type] || type}</h3>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-text-secondary">
                    {items.length}
                  </span>
                </div>
                <div className="divide-y divide-border">
                  {items.map((item) => (
                    <div key={item.id} className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors">
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
