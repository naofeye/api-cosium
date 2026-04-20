import { cn } from "@/lib/utils";
import { Check, Minus } from "lucide-react";

interface QuoteLineItem {
  label: string;
  price?: number | null;
}

interface Quote {
  id: number | string;
  numero?: string;
  title?: string;
  lines: QuoteLineItem[];
  total: number;
  reste_a_charge?: number | null;
  highlighted?: boolean;
}

interface QuoteComparisonProps {
  quotes: Quote[];
  className?: string;
}

/**
 * Comparatif devis cote a cote (2 a 3 options max).
 * Aligne les lignes ayant le meme label pour comparaison visuelle.
 */
export function QuoteComparison({ quotes, className }: QuoteComparisonProps) {
  if (quotes.length === 0) return null;

  // Consolide tous les labels uniques pour aligner les lignes
  const allLabels: string[] = [];
  for (const q of quotes) {
    for (const l of q.lines) {
      if (!allLabels.includes(l.label)) allLabels.push(l.label);
    }
  }

  return (
    <div className={cn("grid gap-4", `md:grid-cols-${Math.min(quotes.length, 3)}`, className)}>
      {quotes.map((q) => (
        <div
          key={q.id}
          className={cn(
            "rounded-xl border p-5 shadow-sm flex flex-col",
            q.highlighted
              ? "border-primary bg-blue-50/60 ring-2 ring-primary/20"
              : "border-border bg-bg-card",
          )}
        >
          <div className="mb-4">
            {q.numero && (
              <p className="text-xs text-text-secondary font-mono">#{q.numero}</p>
            )}
            <h3 className="text-base font-semibold text-text-primary mt-0.5">
              {q.title ?? `Option ${q.id}`}
            </h3>
            {q.highlighted && (
              <span className="inline-flex items-center gap-1 mt-2 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                <Check className="h-3 w-3" aria-hidden="true" /> Recommande
              </span>
            )}
          </div>

          <ul className="space-y-2 flex-1 mb-4">
            {allLabels.map((label) => {
              const line = q.lines.find((l) => l.label === label);
              return (
                <li
                  key={label}
                  className="flex items-center justify-between gap-3 text-sm border-b border-border/50 pb-1.5 last:border-0"
                >
                  <span className="flex items-center gap-2 text-text-primary">
                    {line ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                    ) : (
                      <Minus className="h-3.5 w-3.5 text-gray-400" aria-hidden="true" />
                    )}
                    <span className={line ? "" : "text-text-secondary line-through"}>{label}</span>
                  </span>
                  {line?.price != null && (
                    <span className="tabular-nums text-text-secondary">
                      {line.price.toLocaleString("fr-FR", { minimumFractionDigits: 2 })} EUR
                    </span>
                  )}
                </li>
              );
            })}
          </ul>

          <div className="pt-3 border-t border-border space-y-1">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-text-secondary">Total TTC</span>
              <span className="text-lg font-bold tabular-nums">
                {q.total.toLocaleString("fr-FR", { minimumFractionDigits: 2 })} EUR
              </span>
            </div>
            {q.reste_a_charge != null && (
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-text-secondary">Reste a charge</span>
                <span className="text-sm font-semibold text-amber-700 tabular-nums">
                  {q.reste_a_charge.toLocaleString("fr-FR", { minimumFractionDigits: 2 })} EUR
                </span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
