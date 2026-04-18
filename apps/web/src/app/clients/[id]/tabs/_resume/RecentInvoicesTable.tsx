import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import type { CosiumInvoice } from "./types";

export function RecentInvoicesTable({ invoices }: { invoices: CosiumInvoice[] }) {
  if (invoices.length === 0) return null;
  const recent = invoices.slice(0, 5);

  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      <div className="px-6 py-3 border-b">
        <h3 className="text-sm font-semibold">Dernieres factures Cosium</h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-text-secondary">
            <th className="px-4 py-2 text-left font-medium">Numero</th>
            <th className="px-4 py-2 text-left font-medium">Date</th>
            <th className="px-4 py-2 text-left font-medium">Type</th>
            <th className="px-4 py-2 text-right font-medium">Montant TTC</th>
            <th className="px-4 py-2 text-center font-medium">Solde</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((inv) => (
            <tr key={inv.cosium_id} className="border-b last:border-0">
              <td className="px-4 py-2 font-mono">{inv.invoice_number}</td>
              <td className="px-4 py-2">
                {inv.invoice_date ? <DateDisplay date={inv.invoice_date} /> : "-"}
              </td>
              <td className="px-4 py-2">{inv.type}</td>
              <td className="px-4 py-2 text-right">
                <MoneyDisplay amount={inv.total_ti} bold />
              </td>
              <td className="px-4 py-2 text-center">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                    inv.settled
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-amber-50 text-amber-700"
                  }`}
                >
                  {inv.settled ? "Solde" : "Non solde"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
