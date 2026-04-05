"use client";

import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";

interface Devis {
  id: number;
  numero: string;
  statut: string;
  montant_ttc: number;
  reste_a_charge: number;
}

interface Facture {
  id: number;
  numero: string;
  statut: string;
  montant_ttc: number;
  date_emission: string;
}

interface Paiement {
  id: number;
  payeur: string;
  mode: string | null;
  montant_du: number;
  montant_paye: number;
  statut: string;
}

interface CosiumInvoice {
  cosium_id: number;
  invoice_number: string;
  invoice_date: string | null;
  type: string;
  total_ti: number;
  outstanding_balance: number;
  share_social_security: number;
  share_private_insurance: number;
  settled: boolean;
}

interface TabFinancesProps {
  devis: Devis[];
  factures: Facture[];
  paiements: Paiement[];
  cosiumInvoices?: CosiumInvoice[];
}

export function TabFinances({ devis, factures, paiements, cosiumInvoices = [] }: TabFinancesProps) {
  const router = useRouter();

  const hasData = devis.length > 0 || factures.length > 0 || paiements.length > 0 || cosiumInvoices.length > 0;

  if (!hasData) {
    return <EmptyState title="Aucune donnee financiere" description="Les devis, factures et paiements apparaitront ici." />;
  }

  return (
    <div className="space-y-6">
      {/* Cosium invoices */}
      {cosiumInvoices.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm">
          <div className="px-5 py-3 border-b">
            <h4 className="text-sm font-semibold">Factures Cosium ({cosiumInvoices.length})</h4>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Numero</th>
                  <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Date</th>
                  <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Type</th>
                  <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">TTC</th>
                  <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">Secu</th>
                  <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">Mutuelle</th>
                  <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">Solde restant</th>
                  <th scope="col" className="px-4 py-2 text-center text-text-secondary font-medium">Statut</th>
                </tr>
              </thead>
              <tbody>
                {cosiumInvoices.map((inv) => (
                  <tr key={inv.cosium_id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono">{inv.invoice_number}</td>
                    <td className="px-4 py-2">
                      {inv.invoice_date ? <DateDisplay date={inv.invoice_date} /> : "-"}
                    </td>
                    <td className="px-4 py-2">{inv.type}</td>
                    <td className="px-4 py-2 text-right">
                      <MoneyDisplay amount={inv.total_ti} bold />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <MoneyDisplay amount={inv.share_social_security} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <MoneyDisplay amount={inv.share_private_insurance} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <MoneyDisplay
                        amount={inv.outstanding_balance}
                        colored
                        className={inv.outstanding_balance > 0 ? "text-red-600" : "text-emerald-600"}
                      />
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
        </div>
      )}

      {/* OptiFlow devis */}
      {devis.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm">
          <div className="px-5 py-3 border-b">
            <h4 className="text-sm font-semibold">Devis ({devis.length})</h4>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Numero</th>
                <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Statut</th>
                <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">TTC</th>
                <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">RAC</th>
              </tr>
            </thead>
            <tbody>
              {devis.map((d) => (
                <tr
                  key={d.id}
                  className="border-b last:border-0 cursor-pointer hover:bg-gray-50"
                  onClick={() => router.push(`/devis/${d.id}`)}
                >
                  <td className="px-4 py-2 font-mono">{d.numero}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={d.statut} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <MoneyDisplay amount={d.montant_ttc} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <MoneyDisplay amount={d.reste_a_charge} colored />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* OptiFlow factures */}
      {factures.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm">
          <div className="px-5 py-3 border-b">
            <h4 className="text-sm font-semibold">Factures ({factures.length})</h4>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Numero</th>
                <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Statut</th>
                <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">TTC</th>
                <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {factures.map((f) => (
                <tr
                  key={f.id}
                  className="border-b last:border-0 cursor-pointer hover:bg-gray-50"
                  onClick={() => router.push(`/factures/${f.id}`)}
                >
                  <td className="px-4 py-2 font-mono">{f.numero}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={f.statut} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <MoneyDisplay amount={f.montant_ttc} bold />
                  </td>
                  <td className="px-4 py-2">
                    <DateDisplay date={f.date_emission} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* OptiFlow paiements */}
      {paiements.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm">
          <div className="px-5 py-3 border-b">
            <h4 className="text-sm font-semibold">Paiements ({paiements.length})</h4>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Payeur</th>
                <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">Du</th>
                <th scope="col" className="px-4 py-2 text-right text-text-secondary font-medium">Paye</th>
                <th scope="col" className="px-4 py-2 text-left text-text-secondary font-medium">Statut</th>
              </tr>
            </thead>
            <tbody>
              {paiements.map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="px-4 py-2 capitalize">{p.payeur}</td>
                  <td className="px-4 py-2 text-right">
                    <MoneyDisplay amount={p.montant_du} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <MoneyDisplay amount={p.montant_paye} colored />
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={p.statut} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
