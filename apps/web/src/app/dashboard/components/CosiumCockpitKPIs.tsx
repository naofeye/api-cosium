"use client";

import useSWR from "swr";
import { KPICard } from "@/components/ui/KPICard";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { formatMoney, formatPercent } from "@/lib/format";
import {
  Euro,
  TrendingUp,
  TrendingDown,
  ShoppingCart,
  Repeat,
  AlertTriangle,
  Calendar,
  CalendarDays,
} from "lucide-react";

interface CosiumCockpitData {
  ca_today: number;
  ca_this_week: number;
  ca_this_month: number;
  ca_last_month: number;
  ca_same_month_last_year: number;
  panier_moyen: number;
  nb_invoices_today: number;
  nb_invoices_this_month: number;
  quote_to_invoice_rate: number;
  aging_0_30: number;
  aging_30_60: number;
  aging_60_90: number;
  aging_over_90: number;
  aging_total: number;
}

function trendVsLastMonth(current: number, previous: number): { value: number; label: string } | undefined {
  if (previous === 0) return undefined;
  const delta = ((current - previous) / previous) * 100;
  return { value: Math.round(delta * 10) / 10, label: "vs mois precedent" };
}

function trendVsLastYear(current: number, previous: number): { value: number; label: string } | undefined {
  if (previous === 0) return undefined;
  const delta = ((current - previous) / previous) * 100;
  return { value: Math.round(delta * 10) / 10, label: "vs N-1" };
}

export function CosiumCockpitKPIs() {
  const { data, error, isLoading } = useSWR<CosiumCockpitData>("/dashboard/cosium-cockpit", {
    refreshInterval: 60000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
      </div>
    );
  }

  if (error || !data) return null;

  const trendMonth = trendVsLastMonth(data.ca_this_month, data.ca_last_month);
  const trendYear = trendVsLastYear(data.ca_this_month, data.ca_same_month_last_year);

  return (
    <div className="space-y-4 mb-8">
      {/* CA temps reel */}
      <div>
        <h3 className="text-sm font-semibold text-text-secondary mb-3 uppercase tracking-wide">Cockpit Cosium - Chiffre d'affaires</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            icon={Euro}
            label={`CA aujourd'hui (${data.nb_invoices_today})`}
            value={formatMoney(data.ca_today)}
            color="primary"
          />
          <KPICard
            icon={CalendarDays}
            label="CA semaine"
            value={formatMoney(data.ca_this_week)}
            color="primary"
          />
          <KPICard
            icon={Calendar}
            label={`CA mois (${data.nb_invoices_this_month})`}
            value={formatMoney(data.ca_this_month)}
            trend={trendMonth ?? trendYear}
            color="success"
          />
          <KPICard
            icon={ShoppingCart}
            label="Panier moyen mois"
            value={formatMoney(data.panier_moyen)}
            color="info"
          />
        </div>
      </div>

      {/* Performance commerciale + balance agee */}
      <div>
        <h3 className="text-sm font-semibold text-text-secondary mb-3 uppercase tracking-wide">Performance & impayes</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KPICard
            icon={Repeat}
            label="Taux transformation 90j"
            value={formatPercent(data.quote_to_invoice_rate)}
            color={data.quote_to_invoice_rate >= 70 ? "success" : data.quote_to_invoice_rate >= 50 ? "warning" : "danger"}
          />
          <KPICard
            icon={AlertTriangle}
            label={`Impaye total (>90j: ${formatMoney(data.aging_over_90)})`}
            value={formatMoney(data.aging_total)}
            color={data.aging_over_90 > 0 ? "danger" : "warning"}
          />
          <KPICard
            icon={TrendingUp}
            label="Mois precedent"
            value={formatMoney(data.ca_last_month)}
            color="info"
          />
          <KPICard
            icon={TrendingDown}
            label="Meme mois N-1"
            value={formatMoney(data.ca_same_month_last_year)}
            color="info"
          />
        </div>
      </div>
    </div>
  );
}
