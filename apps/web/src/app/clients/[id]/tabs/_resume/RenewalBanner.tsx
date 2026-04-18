import Link from "next/link";
import { RefreshCw } from "lucide-react";

export function RenewalBanner({ renewalMonths }: { renewalMonths: number }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
      <RefreshCw className="h-5 w-5 text-amber-600 shrink-0" />
      <div className="flex-1">
        <p className="text-sm font-medium text-amber-900">Eligible au renouvellement</p>
        <p className="text-xs text-amber-700">
          Dernier equipement achete il y a {renewalMonths} mois. Pensez a proposer un
          renouvellement.
        </p>
      </div>
      <Link
        href="/renewals"
        className="text-xs font-medium text-amber-700 hover:underline whitespace-nowrap"
      >
        Voir les opportunites &rarr;
      </Link>
    </div>
  );
}
