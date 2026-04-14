"use client";

import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatMoney } from "@/lib/format";
import { TrendingUp } from "lucide-react";

interface BreakdownRow {
  type: string;
  count: number;
  total_ti: number;
  outstanding: number;
  share_social_security: number;
  share_private_insurance: number;
  share_remaining: number;
}

interface Breakdown {
  breakdown: BreakdownRow[];
  grand_total_ti: number;
  date_from: string | null;
  date_to: string | null;
}

const TYPE_LABELS: Record<string, string> = {
  INVOICE: "Factures",
  QUOTE: "Devis",
  CREDIT_NOTE: "Avoirs",
  DELIVERY_NOTE: "Bons de livraison",
  SHIPPING_FORM: "Bordereaux d'expedition",
  ORDER_FORM: "Bons de commande",
  VALUED_NOTE: "Notes valorisees",
  RETURN_VOUCHER: "Bons de retour",
  SUPPLIER_ORDER_FORM: "Cmd fournisseur",
  SUPPLIER_DELIVERY_NOTE: "Livraison fournisseur",
  SUPPLIER_INVOICE: "Facture fournisseur",
  SUPPLIER_CREDIT_NOTE: "Avoir fournisseur",
  SUPPLIER_VALUED_NOTE: "Note val. fournisseur",
  SUPPLIER_RETURN_VOUCHER: "Retour fournisseur",
  STOCK_MOVE: "Mouvement stock",
  STOCK_MANUAL_UPDATE: "MAJ stock manuelle",
};

const TYPE_COLOR: Record<string, string> = {
  INVOICE: "bg-emerald-100 text-emerald-800",
  QUOTE: "bg-blue-100 text-blue-800",
  CREDIT_NOTE: "bg-amber-100 text-amber-800",
};

export default function AnalyticsCosiumPage() {
  const { data, error, isLoading, mutate } = useSWR<Breakdown>("/analytics/financial-breakdown", {
    refreshInterval: 300000,
  });

  return (
    <PageLayout
      title="Analyse financiere Cosium"
      description="Ventilation comptable par type de document : count, total TI, parts SS / AMC / Reste a charge."
      breadcrumb={[{ label: "Cosium" }, { label: "Analyse financiere" }]}
    >
      {isLoading && <LoadingState text="Chargement de la ventilation..." />}
      {error && <ErrorState message="Impossible de charger la ventilation" onRetry={() => mutate()} />}
      {data && data.breakdown.length === 0 && <EmptyState title="Aucune donnee" description="Aucune facture Cosium synchronisee." />}
      {data && data.breakdown.length > 0 && (
        <>
          <div className="rounded-xl border border-border bg-bg-card p-4 mb-4 shadow-sm flex items-center gap-3">
            <TrendingUp className="h-6 w-6 text-primary" />
            <div>
              <p className="text-xs text-text-secondary uppercase font-semibold tracking-wide">Total tous types</p>
              <p className="text-2xl font-bold tabular-nums text-text-primary">{formatMoney(data.grand_total_ti)}</p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-text-secondary font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-right">Nb</th>
                  <th className="px-4 py-3 text-right">Total TI</th>
                  <th className="px-4 py-3 text-right">Part Secu</th>
                  <th className="px-4 py-3 text-right">Part AMC</th>
                  <th className="px-4 py-3 text-right">Reste a charge</th>
                  <th className="px-4 py-3 text-right">Encours</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.breakdown.map((row) => (
                  <tr key={row.type} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${TYPE_COLOR[row.type] ?? "bg-gray-100 text-gray-700"}`}>
                        {TYPE_LABELS[row.type] ?? row.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{row.count.toLocaleString("fr-FR")}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold">{formatMoney(row.total_ti)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-text-secondary">{formatMoney(row.share_social_security)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-text-secondary">{formatMoney(row.share_private_insurance)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{formatMoney(row.share_remaining)}</td>
                    <td className={`px-4 py-3 text-right tabular-nums font-semibold ${row.outstanding > 0 ? "text-red-700" : "text-emerald-700"}`}>
                      {formatMoney(row.outstanding)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </PageLayout>
  );
}
