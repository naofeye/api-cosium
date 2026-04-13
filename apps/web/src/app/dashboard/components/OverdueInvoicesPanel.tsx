import Link from "next/link";
import { Users } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { OverdueInvoice } from "../types";

function rowClasses(daysOverdue: number) {
  if (daysOverdue > 60) return { color: "text-danger", border: "border-l-red-500" };
  if (daysOverdue > 30) return { color: "text-amber-600", border: "border-l-amber-500" };
  return { color: "text-text-secondary", border: "border-l-gray-300" };
}

export function OverdueInvoicesPanel({ invoices }: { invoices: OverdueInvoice[] }) {
  if (invoices.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-8 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-danger" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
            Clients a relancer
          </h3>
        </div>
        <Link href="/relances" className="text-xs font-medium text-primary hover:underline">
          Voir toutes les relances &rarr;
        </Link>
      </div>
      <div className="space-y-2">
        {invoices.map((inv) => {
          const { color, border } = rowClasses(inv.days_overdue);
          return (
            <div
              key={inv.id}
              className={`flex items-center justify-between text-sm rounded-lg px-4 py-3 border-l-4 ${border} bg-gray-50/50 dark:bg-gray-800/20 hover:bg-gray-100/80 dark:hover:bg-gray-700/30 transition-colors`}
            >
              <span className="font-medium text-text-primary truncate">{inv.customer_name}</span>
              <div className="flex items-center gap-4 shrink-0">
                <span className="font-semibold tabular-nums">{formatMoney(inv.montant_ttc)}</span>
                <span className={`text-xs font-medium ${color}`}>
                  {inv.days_overdue}j de retard
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
