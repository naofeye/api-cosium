import { formatMoney } from "@/lib/format";
import { RefreshCw } from "lucide-react";
import Link from "next/link";

interface RenewalData {
  total_opportunities: number;
  high_score_count: number;
  estimated_revenue: number;
}

interface RenewalSectionProps {
  renewalData: RenewalData | undefined;
}

export function RenewalSection({ renewalData }: RenewalSectionProps) {
  if (!renewalData || renewalData.total_opportunities === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <RefreshCw className="h-5 w-5" /> Renouvellements du mois
        </h3>
        <Link href="/renewals" className="text-sm text-primary hover:underline">
          Voir tout →
        </Link>
      </div>
      <div className="grid grid-cols-3 gap-6">
        <div className="text-center">
          <p className="text-2xl font-bold text-primary tabular-nums">{renewalData.total_opportunities}</p>
          <p className="text-sm text-text-secondary mt-1">Opportunites</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-success tabular-nums">{renewalData.high_score_count}</p>
          <p className="text-sm text-text-secondary mt-1">Fort potentiel</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-warning tabular-nums">
            {formatMoney(renewalData.estimated_revenue)}
          </p>
          <p className="text-sm text-text-secondary mt-1">CA potentiel</p>
        </div>
      </div>
    </div>
  );
}
