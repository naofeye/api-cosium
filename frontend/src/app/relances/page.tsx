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
import {
  Euro,
  Send,
  TrendingUp,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  Clock,
  MessageSquare,
  Calendar,
  ArrowRight,
  Plus,
  Mail,
} from "lucide-react";
import Link from "next/link";

interface OverdueItem {
  entity_type: string;
  entity_id: number;
  customer_name: string;
  payer_type: string;
  amount: number;
  days_overdue: number;
  score: number;
  action: string;
  last_reminder_date?: string | null;
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
  customer_name?: string | null;
}

type Tab = "overdue" | "clients30" | "historique" | "timeline";

const AGE_COLORS: Record<string, string> = {
  "0-30j": "bg-emerald-500",
  "30-60j": "bg-amber-500",
  "60-90j": "bg-orange-500",
  "90j+": "bg-red-500",
};

const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  email: <Mail className="h-3.5 w-3.5" />,
  courrier: <MessageSquare className="h-3.5 w-3.5" />,
  telephone: <MessageSquare className="h-3.5 w-3.5" />,
  sms: <Send className="h-3.5 w-3.5" />,
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
  } = useSWR<{ items: ReminderItem[]; total: number }>("/reminders?limit=50");
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
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Relances" }]}>
        <LoadingState text="Chargement du recouvrement..." />
      </PageLayout>
    );
  if (error)
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Relances" }]}>
        <ErrorState message={error} onRetry={mutateAll} />
      </PageLayout>
    );
  if (!stats) return null;

  const maxAge = Math.max(...Object.values(stats.overdue_by_age), 1);

  /* ─── Derived KPIs ─── */
  const plannedCount = reminders.filter((r) => r.status === "planifiee" || r.status === "pending").length;
  const sentCount = reminders.filter((r) => r.status === "envoyee" || r.status === "sent").length;
  const waitingCount = reminders.filter((r) => r.status === "en_attente" || r.status === "waiting").length;
  const respondedCount = reminders.filter((r) => r.status === "repondue" || r.status === "responded").length;

  /* Clients with > 30 days overdue */
  const clients30 = (overdue ?? []).filter((item) => item.days_overdue > 30);

  /* Timeline: last 10 reminders sorted by date */
  const timelineItems = [...reminders]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 10);

  return (
    <PageLayout
      title="Relances et recouvrement"
      description="Suivi des impayes et relances"
      breadcrumb={[{ label: "Relances" }]}
      actions={
        <Link href="/relances/plans">
          <Button variant="outline">
            <Calendar className="h-4 w-4" /> Plans de relance
          </Button>
        </Link>
      }
    >
      {/* KPI cards - 2 rows */}
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard icon={Clock} label="Planifiees" value={plannedCount} color="info" />
        <KPICard icon={Send} label="Envoyees" value={sentCount} color="primary" />
        <KPICard icon={AlertTriangle} label="En attente de reponse" value={waitingCount} color="warning" />
        <KPICard icon={MessageSquare} label="Repondues" value={respondedCount} color="success" />
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

      {/* Tabs */}
      <div className="border-b border-border mb-6">
        <div className="flex gap-0 overflow-x-auto" role="tablist" aria-label="Sections relances">
          {[
            { key: "overdue" as const, label: `A relancer (${overdue?.length ?? 0})` },
            { key: "clients30" as const, label: `Impayes > 30j (${clients30.length})` },
            { key: "timeline" as const, label: "Chronologie" },
            { key: "historique" as const, label: `Historique (${reminders.length})` },
          ].map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              id={`tab-${tab.key}`}
              onClick={() => setActiveTab(tab.key)}
              className={`shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none ${
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

      {/* Tab: A relancer */}
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

      {/* Tab: Clients a relancer > 30 jours */}
      {activeTab === "clients30" &&
        (clients30.length === 0 ? (
          <EmptyState
            title="Aucun impaye de plus de 30 jours"
            description="Tous les clients sont a jour ou en retard de moins de 30 jours."
          />
        ) : (
          <div className="rounded-xl border border-border bg-bg-card shadow-sm">
            <div className="px-5 py-3 border-b border-border">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Clients avec factures impayees depuis plus de 30 jours
              </h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50">
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Client</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Type payeur</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Montant du</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Jours de retard</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Derniere relance</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Action</th>
                </tr>
              </thead>
              <tbody>
                {clients30.map((item) => (
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
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                          item.days_overdue > 90
                            ? "bg-red-100 text-red-700"
                            : item.days_overdue > 60
                              ? "bg-orange-100 text-orange-700"
                              : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {item.days_overdue}j
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-text-secondary">
                      {item.last_reminder_date ? formatDate(item.last_reminder_date) : "Jamais"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          /* navigate to create reminder - future feature */
                        }}
                        aria-label={`Creer une relance pour ${item.customer_name}`}
                      >
                        <Plus className="h-3.5 w-3.5" /> Relancer
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

      {/* Tab: Timeline (visual chronology of recent reminders) */}
      {activeTab === "timeline" &&
        (timelineItems.length === 0 ? (
          <EmptyState title="Aucune relance" description="L'historique des relances apparaitra ici." />
        ) : (
          <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-text-primary mb-6 flex items-center gap-2">
              <Clock className="h-5 w-5" /> Chronologie des relances recentes
            </h3>
            <div className="relative">
              {/* vertical line */}
              <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

              <div className="space-y-6">
                {timelineItems.map((r, idx) => {
                  const isSent = r.status === "envoyee" || r.status === "sent";
                  const isResponded = r.status === "repondue" || r.status === "responded";
                  const isFailed = r.status === "echouee" || r.status === "failed";

                  return (
                    <div key={r.id} className="relative flex items-start gap-4 pl-2">
                      {/* dot */}
                      <div
                        className={`relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 ${
                          isResponded
                            ? "bg-emerald-100 border-emerald-500"
                            : isFailed
                              ? "bg-red-100 border-red-500"
                              : isSent
                                ? "bg-blue-100 border-blue-500"
                                : "bg-gray-100 border-gray-400"
                        }`}
                      >
                        {isResponded ? (
                          <CheckCircle className="h-4 w-4 text-emerald-600" />
                        ) : isFailed ? (
                          <AlertTriangle className="h-4 w-4 text-red-600" />
                        ) : (
                          (CHANNEL_ICONS[r.channel] || <Send className="h-4 w-4 text-blue-600" />)
                        )}
                      </div>

                      {/* content */}
                      <div className="flex-1 min-w-0 pb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-text-primary">
                            Relance #{r.id}
                          </span>
                          <StatusBadge status={r.status} />
                          <span className="text-xs text-text-secondary capitalize">{r.channel}</span>
                        </div>
                        {r.content && (
                          <p className="mt-1 text-sm text-text-secondary truncate max-w-md">{r.content}</p>
                        )}
                        <p className="mt-1 text-xs text-text-secondary">
                          {formatDate(r.created_at)}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ))}

      {/* Tab: Historique (table) */}
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
