"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { formatMoney } from "@/lib/format";
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
} from "lucide-react";
import Link from "next/link";
import { OverdueTab } from "./components/OverdueTab";
import { Clients30Tab } from "./components/Clients30Tab";
import { TimelineTab } from "./components/TimelineTab";
import { HistoriqueTab } from "./components/HistoriqueTab";

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

  /* Derived KPIs */
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

  const tabs = [
    { key: "overdue" as const, label: `A relancer (${overdue?.length ?? 0})` },
    { key: "clients30" as const, label: `Impayes > 30j (${clients30.length})` },
    { key: "timeline" as const, label: "Chronologie" },
    { key: "historique" as const, label: `Historique (${reminders.length})` },
  ];

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
          {tabs.map((tab) => (
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

      {/* Tab content */}
      {activeTab === "overdue" && <OverdueTab items={overdue ?? []} />}
      {activeTab === "clients30" && <Clients30Tab items={clients30} />}
      {activeTab === "timeline" && <TimelineTab items={timelineItems} />}
      {activeTab === "historique" && <HistoriqueTab items={reminders} />}
    </PageLayout>
  );
}
