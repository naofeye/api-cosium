"use client";

import { AlertTriangle, Plus } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/format";

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

interface Clients30TabProps {
  items: OverdueItem[];
}

export function Clients30Tab({ items }: Clients30TabProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Aucun impaye de plus de 30 jours"
        description="Tous les clients sont a jour ou en retard de moins de 30 jours."
      />
    );
  }

  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      <div className="px-5 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          Clients avec factures impayees depuis plus de 30 jours
        </h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-gray-50">
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Client</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Type payeur</th>
            <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Montant du</th>
            <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Jours de retard</th>
            <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Derniere relance</th>
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
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                    item.days_overdue > 90
                      ? "bg-red-100 text-red-700"
                      : item.days_overdue > 60
                        ? "bg-orange-100 text-orange-700"
                        : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {item.days_overdue}j
                </span>
              </td>
              <td className="px-4 py-3 text-center text-xs text-text-secondary">
                {item.last_reminder_date ? formatDate(item.last_reminder_date) : "Jamais"}
              </td>
              <td className="px-4 py-3 text-center">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    /* navigate to create reminder - future feature */
                  }}
                  aria-label={`Creer une relance pour ${item.customer_name}`}
                >
                  <Plus className="h-3.5 w-3.5" /> Relancer
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
