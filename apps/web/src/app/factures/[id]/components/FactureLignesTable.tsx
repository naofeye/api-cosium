"use client";

import { formatMoney } from "@/lib/format";
import type { FactureLigne } from "../types";

interface FactureLignesTableProps {
  lignes: FactureLigne[];
  montant_ht: number;
  montant_ttc: number;
}

export function FactureLignesTable({ lignes, montant_ht, montant_ttc }: FactureLignesTableProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      <div className="px-5 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-text-primary">Lignes ({lignes.length})</h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-gray-50">
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Designation</th>
            <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Qte</th>
            <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">PU HT</th>
            <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">TVA %</th>
            <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">HT</th>
            <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">TTC</th>
          </tr>
        </thead>
        <tbody>
          {lignes.map((l) => (
            <tr key={l.id} className="border-b border-border last:border-0">
              <td className="px-4 py-3 font-medium">{l.designation}</td>
              <td className="px-4 py-3 text-center">{l.quantite}</td>
              <td className="px-4 py-3 text-right tabular-nums">{formatMoney(l.prix_unitaire_ht)}</td>
              <td className="px-4 py-3 text-center">{l.taux_tva}%</td>
              <td className="px-4 py-3 text-right tabular-nums">{formatMoney(l.montant_ht)}</td>
              <td className="px-4 py-3 text-right tabular-nums font-medium">{formatMoney(l.montant_ttc)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-gray-50 font-semibold">
            <td colSpan={4} className="px-4 py-3">Total</td>
            <td className="px-4 py-3 text-right tabular-nums">{formatMoney(montant_ht)}</td>
            <td className="px-4 py-3 text-right tabular-nums">{formatMoney(montant_ttc)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
