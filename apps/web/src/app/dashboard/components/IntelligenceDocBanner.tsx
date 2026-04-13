import Link from "next/link";
import { FileSearch } from "lucide-react";
import type { DataQualityData } from "../types";

const TYPE_LABELS: Record<string, string> = {
  ordonnance: "ordonnances",
  devis: "devis",
  attestation_mutuelle: "attestations",
  facture: "factures",
  courrier: "courriers",
  autre: "autres",
};

export function IntelligenceDocBanner({ dataQuality }: { dataQuality: DataQualityData | undefined }) {
  if (!dataQuality?.extractions || dataQuality.extractions.total_extracted === 0) return null;
  const ext = dataQuality.extractions;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
            Intelligence documentaire
          </h3>
        </div>
        <Link href="/admin#data-quality" className="text-xs font-medium text-primary hover:underline">
          Voir le detail &rarr;
        </Link>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
        <span className="font-semibold text-text-primary tabular-nums">
          {ext.total_extracted.toLocaleString("fr-FR")} documents analyses
        </span>
        <span className="text-text-secondary">
          {Object.entries(ext.by_type)
            .map(([type, count]) => `${count.toLocaleString("fr-FR")} ${TYPE_LABELS[type] || type}`)
            .join(" | ")}
        </span>
      </div>
      <div className="mt-2">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${Math.min(ext.extraction_rate, 100)}%` }}
            />
          </div>
          <span className="text-xs text-text-secondary tabular-nums">
            {ext.extraction_rate}% extraits
          </span>
        </div>
      </div>
    </div>
  );
}
