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

interface TabFinancesProps {
  devis: Devis[];
  factures: Facture[];
  paiements: Paiement[];
}

export function TabFinances({ devis, factures, paiements }: TabFinancesProps) {
  const router = useRouter();

  return (
    <div className="space-y-6">
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
      {devis.length === 0 && factures.length === 0 && paiements.length === 0 && (
        <EmptyState title="Aucune donnee financiere" description="Les devis, factures et paiements apparaitront ici." />
      )}
    </div>
  );
}
