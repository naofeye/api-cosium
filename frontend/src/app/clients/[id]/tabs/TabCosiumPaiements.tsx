"use client";

import useSWR from "swr";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { CosiumPaymentItem } from "@/lib/types";

interface TabCosiumPaiementsProps {
  cosiumId: string | number | null;
}

function paymentTypeLabel(type: string): string {
  switch (type?.toUpperCase()) {
    case "CHQ": return "Cheque";
    case "CB": return "Carte bancaire";
    case "ESP": return "Especes";
    case "VIR": return "Virement";
    default: return type || "-";
  }
}

export function TabCosiumPaiements({ cosiumId }: TabCosiumPaiementsProps) {
  const { data, error, isLoading, mutate } = useSWR<{ items: CosiumPaymentItem[] }>(
    cosiumId ? `/cosium/payments?customer_id=${cosiumId}&page_size=50` : null,
  );

  if (!cosiumId) {
    return (
      <EmptyState
        title="Client non lie a Cosium"
        description="Ce client n'a pas d'identifiant Cosium. L'historique de paiements ne peut pas etre recupere."
      />
    );
  }

  if (isLoading) return <LoadingState text="Chargement des paiements Cosium..." />;
  if (error) return <ErrorState message={error.message ?? "Erreur de chargement"} onRetry={() => mutate()} />;

  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <EmptyState
        title="Aucun paiement Cosium"
        description="Aucun paiement trouve pour ce client dans Cosium."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th className="py-2 px-3 font-medium">Date</th>
            <th className="py-2 px-3 font-medium">Type</th>
            <th className="py-2 px-3 font-medium text-right">Montant</th>
            <th className="py-2 px-3 font-medium">Banque</th>
            <th className="py-2 px-3 font-medium">Reference</th>
            <th className="py-2 px-3 font-medium">Site</th>
          </tr>
        </thead>
        <tbody>
          {items.map((pay) => (
            <tr key={pay.id} className="border-b border-border hover:bg-gray-50">
              <td className="py-2 px-3">
                {pay.due_date ? <DateDisplay date={pay.due_date} /> : "-"}
              </td>
              <td className="py-2 px-3">
                <StatusBadge
                  status={pay.type === "CB" ? "en_cours" : "brouillon"}
                  label={paymentTypeLabel(pay.type)}
                />
              </td>
              <td className="py-2 px-3 text-right">
                <MoneyDisplay
                  amount={pay.amount}
                  bold
                  className={pay.amount >= 0 ? "text-emerald-600" : "text-red-600"}
                />
              </td>
              <td className="py-2 px-3">{pay.bank || "-"}</td>
              <td className="py-2 px-3 font-mono">{pay.payment_number || "-"}</td>
              <td className="py-2 px-3">{pay.site_name || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
