"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { Button } from "@/components/ui/Button";
import { formatMoney, formatDate } from "@/lib/format";
import { Euro, Send, TrendingUp, BarChart3, AlertTriangle, CheckCircle } from "lucide-react";

interface OverdueItem {
  entity_type: string;
  entity_id: number;
  customer_name: string;
  payer_type: string;
  amount: number;
  days_overdue: number;
  score: number;
  action: string;
}

interface Stats {
  total_overdue_amount: number;
  total_reminders_sent: number;
  total_responded: number;
  recovery_rate: number;
  overdue_by_age: Record<string, number>;
}

interface ReminderItem {
  id: number;
  target_type: string;
  target_id: number;
  channel: string;
  status: string;
  content: string | null;
  created_at: string;
}

type Tab = "overdue" | "historique" | "plans";

const AGE_COLORS: Record<string, string> = {
  "0-30j": "bg-emerald-500",
  "30-60j": "bg-amber-500",
  "60-90j": "bg-orange-500",
  "90j+": "bg-red-500",
};

export default function RelancesPage() {
  const {
    data: overdue,
    error: overdueErr,
    isLoading: overdueLoading,
    mutate: mutateOverdue,
  } = useSWR<OverdueItem[]>("/reminders/overdue?min_days=0");
  const {
    data: stats,
    error: statsErr,
    isLoading: statsLoading,
    mutate: mutateStats,
  } = useSWR<Stats>("/reminders/stats");
  const {
    data: remindersData,
    error: remErr,
    isLoading: remLoading,
    mutate: mutateReminders,
  } = useSWR<{ items: ReminderItem[]; total: number }>("/reminders?limit=20");
  const [activeTab, setActiveTab] = useState<Tab>("overdue");

  const isLoading = overdueLoading || statsLoading || remLoading;
  const error = overdueErr?.message ?? statsErr?.message ?? remErr?.message ?? null;
  const reminders = remindersData?.items ?? [];

  const mutateAll = () => {
    mutateOverdue();
    mutateStats();
    mutateReminders();
  };

  if (isLoading)
    return (
      <PageLayout title="Chargement...">
        <LoadingState text="Chargement du recouvrement..." />
      </PageLayout>
    );
  if (error)
    return (
      <PageLayout title="Erreur">
        <ErrorState message={error} onRetry={mutateAll} />
      </PageLayout>
    );
  if (!stats) return null;

  const maxAge = Math.max(...Object.values(stats.overdue_by_age), 1);

  return (
    <PageLayout
      title="Relances et recouvrement"
      description="Suivi des impayees et relances"
      breadcrumb={[{ label: "Relances" }]}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          icon={Euro}
          label="Total impaye"
          value={formatMoney(stats.total_overdue_amount)}
          color={stats.total_overdue_amount > 0 ? "danger" : "success"}
        />
        <KPICard icon={Send} label="Relances envoyees" value={stats.total_reminders_sent} color="info" />
        <KPICard icon={CheckCircle} label="Reponses" value={stats.total_responded} color="success" />
        <KPICard
          icon={TrendingUp}
          label="Taux recouvrement"
          value={`${stats.recovery_rate}%`}
          color={stats.recovery_rate > 50 ? "success" : "warning"}
        />
      </div>

      {/* Balance agee */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5" /> Balance agee
        </h3>
        <div className="grid grid-cols-4 gap-4">
          {Object.entries(stats.overdue_by_age).map(([bucket, amount]) => (
            <div key={bucket}>
              <div className="flex items-end justify-between mb-1">
                <span className="text-xs font-medium text-text-secondary">{bucket}</span>
                <span className="text-xs font-semibold tabular-nums">{formatMoney(amount)}</span>
              </div>
              <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${AGE_COLORS[bucket] || "bg-gray-400"}`}
                  style={{ width: `${(amount / maxAge) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border-b border-border mb-6">
        <div className="flex gap-0" role="tablist" aria-label="Sections relances">
          {[
            { key: "overdue" as const, label: `A relancer (${overdue?.length ?? 0})` },
            { key: "historique" as const, label: `Historique (${reminders.length})` },
          ].map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              id={`tab-${tab.key}`}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "overdue" &&
        ((overdue?.length ?? 0) === 0 ? (
          <EmptyState title="Aucun impaye" description="Toutes les factures sont a jour. Bravo !" />
        ) : (
          <div className="rounded-xl border border-border bg-bg-card shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50">
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Client</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Payeur</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Montant</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Retard</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Score</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Action</th>
                </tr>
              </thead>
              <tbody>
                {(overdue ?? []).map((item) => (
                  <tr
                    key={`${item.entity_type}-${item.entity_id}`}
                    className="border-b border-border last:border-0 hover:bg-gray-50"
                  >
                    <td className="px-4 py-3 font-medium">{item.customer_name}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.payer_type} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <MoneyDisplay amount={item.amount} colored />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`text-xs font-medium ${item.days_overdue > 60 ? "text-red-700" : item.days_overdue > 30 ? "text-amber-700" : "text-text-secondary"}`}
                      >
                        {item.days_overdue}j
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-xs font-semibold tabular-nums">{item.score.toFixed(0)}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 capitalize">
                        {item.action}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

      {activeTab === "historique" &&
        (reminders.length === 0 ? (
          <EmptyState title="Aucune relance" description="L'historique des relances apparaitra ici." />
        ) : (
          <div className="rounded-xl border border-border bg-bg-card shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50">
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">ID</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Canal</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Statut</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Contenu</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
                </tr>
              </thead>
              <tbody>
                {reminders.map((r) => (
                  <tr key={r.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3 font-mono text-text-secondary">#{r.id}</td>
                    <td className="px-4 py-3 capitalize">{r.channel}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate text-text-secondary">{r.content || "-"}</td>
                    <td className="px-4 py-3 text-text-secondary text-xs">
                      {formatDate(r.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </PageLayout>
  );
}
