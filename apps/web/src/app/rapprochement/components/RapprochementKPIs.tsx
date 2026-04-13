import { AlertCircle, BarChart3, CheckCircle, FileText, Link2 } from "lucide-react";
import { KPICard } from "@/components/ui/KPICard";
import { formatMoney } from "@/lib/format";

interface Props {
  totalImported: number;
  matchedCount: number;
  unmatchedCount: number;
  tauxRapprochement: number;
  totalMatched: number;
  totalUnmatched: number;
  paymentsCount: number;
}

function MoneyCard({
  label,
  amount,
  textClass,
  icon: Icon,
  iconClass,
}: {
  label: string;
  amount: number | string;
  textClass: string;
  icon: typeof CheckCircle;
  iconClass: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-xs font-medium text-text-secondary">{label}</p>
        <p className={`text-lg font-bold tabular-nums ${textClass}`}>{amount}</p>
      </div>
      <Icon className={`h-8 w-8 ${iconClass}`} aria-hidden="true" />
    </div>
  );
}

export function RapprochementKPIs({
  totalImported,
  matchedCount,
  unmatchedCount,
  tauxRapprochement,
  totalMatched,
  totalUnmatched,
  paymentsCount,
}: Props) {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard icon={FileText} label="Transactions importees" value={totalImported} color="primary" />
        <KPICard icon={CheckCircle} label="Rapprochees" value={matchedCount} color="success" />
        <KPICard
          icon={AlertCircle}
          label="Non rapprochees"
          value={unmatchedCount}
          color={unmatchedCount > 0 ? "danger" : "success"}
        />
        <KPICard
          icon={BarChart3}
          label="Taux rapprochement"
          value={`${tauxRapprochement}%`}
          color={tauxRapprochement >= 80 ? "success" : tauxRapprochement >= 50 ? "warning" : "danger"}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <MoneyCard
          label="Montant rapproche"
          amount={formatMoney(totalMatched)}
          textClass="text-emerald-700"
          icon={CheckCircle}
          iconClass="text-emerald-200"
        />
        <MoneyCard
          label="Montant non rapproche"
          amount={formatMoney(totalUnmatched)}
          textClass="text-amber-700"
          icon={AlertCircle}
          iconClass="text-amber-200"
        />
        <MoneyCard
          label="Paiements a rapprocher"
          amount={paymentsCount}
          textClass="text-blue-700"
          icon={Link2}
          iconClass="text-blue-200"
        />
      </div>
    </>
  );
}
