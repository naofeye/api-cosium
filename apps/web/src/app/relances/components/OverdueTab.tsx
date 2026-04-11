"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";

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

interface OverdueTabProps {
  items: OverdueItem[];
}

export function OverdueTab({ items }: OverdueTabProps) {
  if (items.length === 0) {
    return <EmptyState title="Aucun impaye" description="Toutes les factures sont a jour. Bravo !" />;
  }

  return (
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
          {items.map((item) => (
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
  );
}
