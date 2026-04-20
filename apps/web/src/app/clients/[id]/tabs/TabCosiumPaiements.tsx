import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface CosiumPaymentSummary {
  id: number;
  cosium_id: number;
  amount: number;
  type: string;
  due_date: string | null;
  issuer_name: string;
  bank: string;
  site_name: string;
  payment_number: string;
  invoice_cosium_id: number | null;
}

interface TabCosiumPaiementsProps {
  payments: CosiumPaymentSummary[];
}

function paymentTypeLabel(type: string): string {
  switch (type?.toUpperCase()) {
    case "CHQ": return "Cheque";
    case "CB": return "Carte bancaire";
    case "ESP": return "Especes";
    case "VIR": return "Virement";
    case "PRÉLÈVEMENT":
    case "PRELEVEMENT": return "Prelevement";
    default: return type || "-";
  }
}

export function TabCosiumPaiements({ payments }: TabCosiumPaiementsProps) {
  if (payments.length === 0) {
    return (
      <EmptyState
        title="Aucun paiement Cosium"
        description="Aucun paiement trouve pour ce client."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th scope="col" className="py-2 px-3 font-medium">Date</th>
            <th scope="col" className="py-2 px-3 font-medium">Type</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">Montant</th>
            <th scope="col" className="py-2 px-3 font-medium">Emetteur</th>
            <th scope="col" className="py-2 px-3 font-medium">Banque</th>
            <th scope="col" className="py-2 px-3 font-medium">Reference</th>
            <th scope="col" className="py-2 px-3 font-medium">Site</th>
          </tr>
        </thead>
        <tbody>
          {payments.map((pay) => (
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
              <td className="py-2 px-3">{pay.issuer_name || "-"}</td>
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
