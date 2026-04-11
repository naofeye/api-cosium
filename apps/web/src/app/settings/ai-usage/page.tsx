"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { cn } from "@/lib/utils";
import { Zap, Hash, DollarSign, Gauge, ChevronLeft, ChevronRight } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface AiUsage {
  total_requests: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_usd: number;
  quota: number;
  quota_remaining: number;
  quota_percent: number;
  plan: string;
}

interface DailyUsage {
  day: number;
  requests: number;
  tokens: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatNumber(n: number): string {
  return new Intl.NumberFormat("fr-FR").format(n);
}

function formatUsd(n: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(n);
}

const MONTH_NAMES = [
  "Janvier",
  "Février",
  "Mars",
  "Avril",
  "Mai",
  "Juin",
  "Juillet",
  "Août",
  "Septembre",
  "Octobre",
  "Novembre",
  "Décembre",
];

function quotaColor(percent: number): string {
  if (percent >= 80) return "bg-red-500";
  if (percent >= 50) return "bg-amber-500";
  return "bg-emerald-500";
}

function quotaTextColor(percent: number): string {
  if (percent >= 80) return "text-red-700";
  if (percent >= 50) return "text-amber-700";
  return "text-emerald-700";
}

/* ------------------------------------------------------------------ */
/* Page component                                                      */
/* ------------------------------------------------------------------ */

export default function AiUsagePage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const {
    data: usage,
    error: usageError,
    isLoading: usageLoading,
    mutate: mutateUsage,
  } = useSWR<AiUsage>(`/ai/usage?year=${year}&month=${month}`);
  const { data: daily = [], isLoading: dailyLoading } = useSWR<DailyUsage[]>(
    `/ai/usage/daily?year=${year}&month=${month}`,
  );

  const loading = usageLoading || dailyLoading;
  const error = usageError?.message ?? null;

  /* ---- Month navigation ---- */

  function prevMonth() {
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else {
      setMonth((m) => m - 1);
    }
  }

  function nextMonth() {
    const isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1;
    if (isCurrentMonth) return;
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else {
      setMonth((m) => m + 1);
    }
  }

  const isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1;

  /* ---- Render ---- */

  if (loading) return <LoadingState text="Chargement de la consommation IA..." />;
  if (error && !usage) return <ErrorState message={error} onRetry={() => mutateUsage()} />;
  if (!usage) return <ErrorState message="Impossible de charger la consommation." onRetry={() => mutateUsage()} />;

  const totalTokens = usage.total_tokens_in + usage.total_tokens_out;

  return (
    <PageLayout
      title="Consommation IA"
      breadcrumb={[{ label: "Parametres", href: "/settings" }, { label: "Consommation IA" }]}
    >
      <div className="space-y-8">
        <section>
          <p className="mt-1 text-sm text-text-secondary">
            Suivi de votre utilisation des assistants IA — plan{" "}
            <span className="font-medium text-gray-700">{usage.plan}</span>.
          </p>
        </section>

        {/* Month selector */}
        <div className="flex items-center gap-4">
          <button
            onClick={prevMonth}
            className="rounded-lg border border-border p-2 hover:bg-gray-50"
            aria-label="Mois précédent"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="min-w-[160px] text-center text-sm font-semibold text-gray-900">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={nextMonth}
            disabled={isCurrentMonth}
            className={cn(
              "rounded-lg border border-border p-2",
              isCurrentMonth ? "cursor-not-allowed opacity-40" : "hover:bg-gray-50",
            )}
            aria-label="Mois suivant"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {/* KPI cards */}
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard icon={Zap} label="Requêtes du mois" value={formatNumber(usage.total_requests)} color="primary" />
          <KPICard icon={Hash} label="Tokens consommés" value={formatNumber(totalTokens)} color="info" />
          <KPICard icon={DollarSign} label="Coût estimé" value={formatUsd(usage.total_cost_usd)} color="warning" />
          <KPICard
            icon={Gauge}
            label="Quota restant"
            value={formatNumber(usage.quota_remaining)}
            color={usage.quota_percent >= 80 ? "danger" : usage.quota_percent >= 50 ? "warning" : "success"}
          />
        </div>

        {/* Quota progress bar */}
        <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">Utilisation du quota</h2>
            <span className={cn("text-sm font-semibold", quotaTextColor(usage.quota_percent))}>
              {usage.quota_percent.toFixed(1)} %
            </span>
          </div>
          <div className="mt-3 h-4 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className={cn("h-full rounded-full transition-all", quotaColor(usage.quota_percent))}
              style={{ width: `${Math.min(usage.quota_percent, 100)}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-xs text-text-secondary">
            <span>{formatNumber(usage.total_requests)} utilisées</span>
            <span>{formatNumber(usage.quota)} quota total</span>
          </div>
          {usage.quota_percent >= 80 && (
            <p className="mt-3 text-sm text-red-700">
              Attention : vous approchez de la limite de votre quota mensuel. Pensez à passer au plan supérieur si
              besoin.
            </p>
          )}
        </div>

        {/* Daily usage table */}
        <div className="rounded-xl border border-border bg-white shadow-sm">
          <div className="border-b border-border px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-800">Détail quotidien</h2>
          </div>
          {daily.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-text-secondary">Aucune consommation pour ce mois.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                    <th scope="col" className="px-6 py-3">Jour</th>
                    <th scope="col" className="px-6 py-3 text-right">Requêtes</th>
                    <th scope="col" className="px-6 py-3 text-right">Tokens</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {daily.map((row) => (
                    <tr key={row.day} className="hover:bg-gray-50">
                      <td className="px-6 py-3 tabular-nums">
                        {String(row.day).padStart(2, "0")}/{String(month).padStart(2, "0")}/{year}
                      </td>
                      <td className="px-6 py-3 text-right tabular-nums">{formatNumber(row.requests)}</td>
                      <td className="px-6 py-3 text-right tabular-nums">{formatNumber(row.tokens)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
