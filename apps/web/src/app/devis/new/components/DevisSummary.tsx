import { formatMoney } from "@/lib/format";

interface DevisSummaryProps {
  totalHT: number;
  totalTVA: number;
  totalTTC: number;
  partSecu: number;
  partMutuelle: number;
  reste: number;
}

export function DevisSummary({
  totalHT,
  totalTVA,
  totalTTC,
  partSecu,
  partMutuelle,
  reste,
}: DevisSummaryProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <h3 className="text-lg font-semibold text-text-primary mb-3">Recapitulatif</h3>
      <div className="space-y-2 text-sm max-w-xs ml-auto">
        <div className="flex justify-between">
          <span className="text-text-secondary">Total HT</span>
          <span className="font-medium tabular-nums">{formatMoney(totalHT)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-secondary">TVA</span>
          <span className="font-medium tabular-nums">{formatMoney(totalTVA)}</span>
        </div>
        <div className="flex justify-between border-t border-border pt-2">
          <span className="font-semibold">Total TTC</span>
          <span className="font-bold tabular-nums">{formatMoney(totalTTC)}</span>
        </div>
        <div className="flex justify-between text-text-secondary">
          <span>Part Secu</span>
          <span className="tabular-nums">- {formatMoney(partSecu)}</span>
        </div>
        <div className="flex justify-between text-text-secondary">
          <span>Part Mutuelle</span>
          <span className="tabular-nums">- {formatMoney(partMutuelle)}</span>
        </div>
        <div className="flex justify-between border-t border-border pt-2">
          <span className="font-semibold text-danger">Reste a charge</span>
          <span className="font-bold tabular-nums text-danger">{formatMoney(reste)}</span>
        </div>
      </div>
    </div>
  );
}
