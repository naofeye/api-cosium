import { DateDisplay } from "@/components/ui/DateDisplay";
import { formatMoney } from "@/lib/format";
import type { DevisDetail } from "./DevisTimeline";

export function DevisFinancialSummary({ devis }: { devis: DevisDetail }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      {/* Info card */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-3">Informations</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Client</span>
            <span className="font-medium">{devis.customer_name || "-"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Dossier</span>
            <a href={`/cases/${devis.case_id}`} className="text-primary hover:underline">
              #{devis.case_id}
            </a>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Date de creation</span>
            <DateDisplay date={devis.created_at} />
          </div>
          {devis.updated_at && (
            <div className="flex justify-between">
              <span className="text-text-secondary">Derniere modification</span>
              <DateDisplay date={devis.updated_at} />
            </div>
          )}
        </div>
      </div>

      {/* Financial summary */}
      <div className="lg:col-span-2 rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-3">Recapitulatif financier</h3>
        <div className="space-y-2 text-sm max-w-sm ml-auto">
          <div className="flex justify-between">
            <span className="text-text-secondary">Total HT</span>
            <span className="font-medium tabular-nums">{formatMoney(devis.montant_ht)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">TVA</span>
            <span className="font-medium tabular-nums">{formatMoney(devis.tva)}</span>
          </div>
          <div className="flex justify-between border-t border-border pt-2">
            <span className="font-semibold">Total TTC</span>
            <span className="font-bold tabular-nums">{formatMoney(devis.montant_ttc)}</span>
          </div>
          <div className="flex justify-between text-text-secondary">
            <span>Part Secu</span>
            <span className="tabular-nums">- {formatMoney(devis.part_secu)}</span>
          </div>
          <div className="flex justify-between text-text-secondary">
            <span>Part Mutuelle</span>
            <span className="tabular-nums">- {formatMoney(devis.part_mutuelle)}</span>
          </div>
          <div className="flex justify-between border-t border-border pt-2">
            <span className="font-semibold text-danger">Reste a charge</span>
            <span className="font-bold tabular-nums text-danger">{formatMoney(devis.reste_a_charge)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
