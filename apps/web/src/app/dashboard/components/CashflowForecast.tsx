"use client";

import useSWR from "swr";
import { Wallet, TrendingDown, AlertOctagon } from "lucide-react";
import { formatMoney } from "@/lib/format";

interface CashflowForecast {
  outstanding_total: number;
  expected_30d: number;
  irrecoverable_risk: number;
  buckets: {
    "0_30": number;
    "30_60": number;
    "60_90": number;
    over_90: number;
  };
}

export function CashflowForecastWidget() {
  const { data, error, isLoading } = useSWR<CashflowForecast>(
    "/analytics/cashflow-forecast",
    { refreshInterval: 300000 },
  );

  if (isLoading || error || !data || data.outstanding_total === 0) return null;

  const recoveryRate = data.outstanding_total > 0 ? (data.expected_30d / data.outstanding_total) * 100 : 0;
  const riskRate = data.outstanding_total > 0 ? (data.irrecoverable_risk / data.outstanding_total) * 100 : 0;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Wallet className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
          Previsionnel tresorerie 30j
        </h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center gap-2 mb-1">
            <Wallet className="h-4 w-4 text-blue-600" />
            <span className="text-xs font-medium text-blue-900 uppercase tracking-wide">Encours total</span>
          </div>
          <p className="text-2xl font-bold tabular-nums text-blue-900">{formatMoney(data.outstanding_total)}</p>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown className="h-4 w-4 text-emerald-600" />
            <span className="text-xs font-medium text-emerald-900 uppercase tracking-wide">Encaissable 30j</span>
          </div>
          <p className="text-2xl font-bold tabular-nums text-emerald-900">{formatMoney(data.expected_30d)}</p>
          <p className="text-xs text-emerald-700 mt-0.5">{recoveryRate.toFixed(0)}% de l'encours</p>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2 mb-1">
            <AlertOctagon className="h-4 w-4 text-red-600" />
            <span className="text-xs font-medium text-red-900 uppercase tracking-wide">Risque irrecouvrable</span>
          </div>
          <p className="text-2xl font-bold tabular-nums text-red-900">{formatMoney(data.irrecoverable_risk)}</p>
          <p className="text-xs text-red-700 mt-0.5">{riskRate.toFixed(0)}% (impayes &gt; 90j)</p>
        </div>
      </div>
      <p className="mt-3 text-[10px] text-text-secondary italic">
        Heuristique : 70% encaissable sur 0-30j · 40% sur 30-60j · 20% sur 60-90j · 5% au-dela.
      </p>
    </div>
  );
}
