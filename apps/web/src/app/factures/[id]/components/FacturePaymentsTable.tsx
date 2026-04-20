"use client";

import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CreditCard } from "lucide-react";
import type { FacturePayment } from "../types";

interface FacturePaymentsTableProps {
  payments: FacturePayment[];
}

export function FacturePaymentsTable({ payments }: FacturePaymentsTableProps) {
  if (payments.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm mb-6">
      <div className="px-5 py-3 border-b border-border flex items-center gap-2">
        <CreditCard className="h-4 w-4 text-text-secondary" />
        <h3 className="text-sm font-semibold text-text-primary">
          Historique des paiements ({payments.length})
        </h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-gray-50">
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Payeur</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Moyen</th>
            <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Montant</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Statut</th>
          </tr>
        </thead>
        <tbody>
          {payments.map((p) => (
            <tr key={p.id} className="border-b border-border last:border-0">
              <td className="px-4 py-3"><DateDisplay date={p.date} /></td>
              <td className="px-4 py-3 capitalize">{p.payer_type}</td>
              <td className="px-4 py-3">{p.method}</td>
              <td className="px-4 py-3 text-right">
                <MoneyDisplay amount={p.amount} colored />
              </td>
              <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
