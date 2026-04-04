"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatMoney } from "@/lib/format";
import type { PaymentSummary } from "./types";

interface TabFinancesProps {
  payments: PaymentSummary;
}

export function TabFinances({ payments }: TabFinancesProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      {payments.items.length === 0 ? (
        <div className="p-6">
          <EmptyState title="Aucun paiement" description="Aucun paiement enregistre pour ce dossier." />
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-gray-50">
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Payeur</th>
              <th className="px-4 py-3 text-right font-medium text-text-secondary">Du</th>
              <th className="px-4 py-3 text-right font-medium text-text-secondary">Paye</th>
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Statut</th>
            </tr>
          </thead>
          <tbody>
            {payments.items.map((p) => (
              <tr key={p.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium capitalize">{p.payer_type}</td>
                <td className="px-4 py-3 text-right">
                  <MoneyDisplay amount={p.amount_due} />
                </td>
                <td className="px-4 py-3 text-right">
                  <MoneyDisplay amount={p.amount_paid} colored />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={p.status} />
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-gray-50 font-semibold">
              <td className="px-4 py-3">Total</td>
              <td className="px-4 py-3 text-right">
                <MoneyDisplay amount={payments.total_due} bold />
              </td>
              <td className="px-4 py-3 text-right">
                <MoneyDisplay amount={payments.total_paid} bold colored />
              </td>
              <td className="px-4 py-3">
                {payments.remaining > 0 ? (
                  <span className="text-danger text-sm">Reste : {formatMoney(payments.remaining)}</span>
                ) : (
                  <span className="text-success text-sm">Solde</span>
                )}
              </td>
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  );
}
