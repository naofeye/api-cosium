import { AlertCircle, CheckCircle } from "lucide-react";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import type { BankTx } from "../types";

export function TransactionsTable({ transactions }: { transactions: BankTx[] }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Toutes les transactions</h2>
      <div className="rounded-xl border border-border bg-bg-card shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-gray-50">
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Libelle</th>
              <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Montant</th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Reference</th>
              <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Statut</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => (
              <tr
                key={tx.id}
                className={`border-b border-border last:border-0 transition-colors ${
                  tx.reconciled
                    ? "bg-emerald-50/40 hover:bg-emerald-50"
                    : "bg-amber-50/30 hover:bg-amber-50"
                }`}
              >
                <td className="px-4 py-3"><DateDisplay date={tx.date} /></td>
                <td className="px-4 py-3 font-medium max-w-xs truncate">{tx.libelle}</td>
                <td className="px-4 py-3 text-right"><MoneyDisplay amount={tx.montant} colored /></td>
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">{tx.reference || "-"}</td>
                <td className="px-4 py-3 text-center">
                  {tx.reconciled ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-100 rounded-full px-2.5 py-0.5">
                      <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" /> Rapprochee
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-100 rounded-full px-2.5 py-0.5">
                      <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" /> Non rapprochee
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
