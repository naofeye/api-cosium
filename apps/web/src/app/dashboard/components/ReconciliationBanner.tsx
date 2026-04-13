import Link from "next/link";
import useSWR from "swr";
import { AlertCircle, ArrowLeftRight } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { ReconciliationSummary } from "../types";

export function ReconciliationBanner() {
  const { data } = useSWR<ReconciliationSummary>("/reconciliation/summary", {
    refreshInterval: 120000,
    onError: () => { /* silent */ },
  });

  if (!data || data.total_customers === 0) return null;

  const tauxSolde = Math.round(
    ((data.solde + data.solde_non_rapproche) / data.total_customers) * 100,
  );
  const anomalies = data.incoherent;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ArrowLeftRight className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
            Rapprochement Cosium
          </h3>
        </div>
        <Link href="/rapprochement-cosium" className="text-xs font-medium text-primary hover:underline">
          Voir le detail &rarr;
        </Link>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-6 text-sm">
        <span className="font-semibold text-text-primary tabular-nums">
          {tauxSolde}% soldes
        </span>
        <span className="text-text-secondary">
          {data.total_customers.toLocaleString("fr-FR")} dossiers analyses
        </span>
        {anomalies > 0 && (
          <span className="inline-flex items-center gap-1 text-red-600 font-medium">
            <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
            {anomalies} anomalie{anomalies > 1 ? "s" : ""}
          </span>
        )}
        {data.total_outstanding > 0 && (
          <span className="text-text-secondary tabular-nums">
            Impaye : {formatMoney(data.total_outstanding)}
          </span>
        )}
      </div>
    </div>
  );
}
