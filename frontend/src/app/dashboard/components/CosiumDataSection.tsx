import { formatMoney } from "@/lib/format";
import { Database } from "lucide-react";
import Link from "next/link";

interface CosiumData {
  total_facture_cosium: number;
  total_outstanding: number;
  total_paid: number;
  invoice_count: number;
  quote_count: number;
  credit_note_count: number;
}

interface CosiumDataSectionProps {
  cosium: CosiumData | null;
}

export function CosiumDataSection({ cosium }: CosiumDataSectionProps) {
  if (!cosium || (cosium.invoice_count === 0 && cosium.quote_count === 0)) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Database className="h-5 w-5" /> Donnees Cosium
        </h3>
        <Link href="/cosium-factures" className="text-sm text-primary hover:underline">
          Voir les factures →
        </Link>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
        <div className="text-center">
          <p className="text-2xl font-bold text-primary tabular-nums">{formatMoney(cosium.total_facture_cosium)}</p>
          <p className="text-sm text-text-secondary mt-1">CA total Cosium</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-success tabular-nums">{formatMoney(cosium.total_paid)}</p>
          <p className="text-sm text-text-secondary mt-1">Encaisse</p>
        </div>
        <div className="text-center">
          <p
            className={`text-2xl font-bold tabular-nums ${cosium.total_outstanding > 0 ? "text-danger" : "text-success"}`}
          >
            {formatMoney(cosium.total_outstanding)}
          </p>
          <p className="text-sm text-text-secondary mt-1">Impaye</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-text-primary tabular-nums">{cosium.invoice_count}</p>
          <p className="text-sm text-text-secondary mt-1">Factures</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-text-primary tabular-nums">{cosium.quote_count}</p>
          <p className="text-sm text-text-secondary mt-1">Devis</p>
        </div>
      </div>
    </div>
  );
}
