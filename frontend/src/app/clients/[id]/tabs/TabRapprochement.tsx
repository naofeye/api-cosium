"use client";

import useSWR from "swr";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { formatMoney } from "@/lib/format";
import {
  ArrowLeftRight,
  AlertCircle,
  CheckCircle,
  Euro,
  Shield,
  CreditCard,
  FileText,
} from "lucide-react";

interface AnomalyItem {
  type: string;
  severity: string;
  message: string;
  invoice_number?: string;
  amount?: number;
}

interface PaymentMatch {
  payment_id: number;
  amount: number;
  type: string;
  category: string;
  issuer_name: string;
}

interface InvoiceReconciliation {
  invoice_id: number;
  invoice_number: string;
  invoice_date: string | null;
  total_ti: number;
  outstanding_balance: number;
  settled: boolean;
  total_paid: number;
  paid_secu: number;
  paid_mutuelle: number;
  paid_client: number;
  paid_avoir: number;
  status: string;
  payments: PaymentMatch[];
  anomalies: AnomalyItem[];
}

interface CustomerReconciliation {
  id: number;
  customer_id: number;
  customer_name: string;
  status: string;
  confidence: string;
  total_facture: number;
  total_outstanding: number;
  total_paid: number;
  total_secu: number;
  total_mutuelle: number;
  total_client: number;
  total_avoir: number;
  invoice_count: number;
  invoices: InvoiceReconciliation[];
  anomalies: AnomalyItem[];
  explanation: string;
}

const CONFIDENCE_LABELS: Record<string, { label: string; className: string }> = {
  certain: { label: "Certain", className: "bg-emerald-100 text-emerald-700" },
  probable: { label: "Probable", className: "bg-blue-100 text-blue-700" },
  partiel: { label: "Partiel", className: "bg-amber-100 text-amber-700" },
  incertain: { label: "Incertain", className: "bg-red-100 text-red-700" },
};

interface TabRapprochementProps {
  clientId: string | number;
}

export function TabRapprochement({ clientId }: TabRapprochementProps) {
  const { data, error, isLoading } = useSWR<CustomerReconciliation>(
    `/reconciliation/customer/${clientId}`,
  );

  if (isLoading) return <LoadingState text="Chargement du rapprochement..." />;
  if (error) return <ErrorState message={error?.message ?? "Erreur lors du chargement"} />;
  if (!data)
    return (
      <EmptyState
        title="Aucun rapprochement"
        description="Les donnees de rapprochement ne sont pas encore disponibles pour ce client."
        icon={ArrowLeftRight}
      />
    );

  const conf = CONFIDENCE_LABELS[data.confidence] ?? CONFIDENCE_LABELS.incertain;

  return (
    <div className="space-y-6">
      {/* Header: status + confidence */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-secondary">Statut :</span>
          <StatusBadge status={data.status} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-secondary">Confiance :</span>
          <span className={`inline-flex items-center text-xs font-medium rounded-full px-2.5 py-0.5 ${conf.className}`}>
            {conf.label}
          </span>
        </div>
      </div>

      {/* Financial breakdown cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <FinCard icon={FileText} label="Total facture" value={data.total_facture} />
        <FinCard icon={CheckCircle} label="Total paye" value={data.total_paid} color="emerald" />
        <FinCard icon={Shield} label="Secu" value={data.total_secu} color="blue" />
        <FinCard icon={Shield} label="Mutuelle" value={data.total_mutuelle} color="blue" />
        <FinCard icon={CreditCard} label="Client" value={data.total_client} color="gray" />
        <FinCard
          icon={Euro}
          label="Reste du"
          value={data.total_outstanding}
          color={data.total_outstanding > 0.01 ? "red" : "emerald"}
        />
      </div>

      {/* Explanation */}
      <div className="rounded-lg border border-border bg-bg-card p-4">
        <p className="text-sm text-text-primary">{data.explanation}</p>
      </div>

      {/* Anomalies */}
      {data.anomalies.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h4 className="text-sm font-semibold text-red-800 mb-2 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            Anomalies detectees ({data.anomalies.length})
          </h4>
          <ul className="space-y-1.5">
            {data.anomalies.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                <span className="shrink-0 mt-0.5 w-1.5 h-1.5 rounded-full bg-red-400" />
                <span>
                  {a.message}
                  {a.amount != null && (
                    <span className="font-semibold ml-1">({formatMoney(a.amount)})</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Per-invoice detail table */}
      {data.invoices.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-3">
            Detail par facture ({data.invoices.length})
          </h4>
          <div className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50">
                  <th scope="col" className="px-4 py-2.5 text-left font-medium text-text-secondary">Facture</th>
                  <th scope="col" className="px-4 py-2.5 text-left font-medium text-text-secondary">Statut</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium text-text-secondary">TTC</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium text-text-secondary">Paye</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium text-text-secondary">Secu</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium text-text-secondary">Mutuelle</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium text-text-secondary">Client</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium text-text-secondary">Reste du</th>
                </tr>
              </thead>
              <tbody>
                {data.invoices.map((inv) => (
                  <tr key={inv.invoice_id} className="border-b border-border last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono text-xs font-medium">{inv.invoice_number}</td>
                    <td className="px-4 py-2.5"><StatusBadge status={inv.status} /></td>
                    <td className="px-4 py-2.5 text-right"><MoneyDisplay amount={inv.total_ti} /></td>
                    <td className="px-4 py-2.5 text-right"><MoneyDisplay amount={inv.total_paid} colored /></td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-text-secondary">{formatMoney(inv.paid_secu)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-text-secondary">{formatMoney(inv.paid_mutuelle)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-text-secondary">{formatMoney(inv.paid_client)}</td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={`font-semibold tabular-nums ${inv.outstanding_balance > 0.01 ? "text-red-600" : "text-emerald-600"}`}>
                        {formatMoney(inv.outstanding_balance)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Helper card ---- */

function FinCard({
  icon: Icon,
  label,
  value,
  color = "gray",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color?: string;
}) {
  const textColors: Record<string, string> = {
    emerald: "text-emerald-700",
    blue: "text-blue-700",
    red: "text-red-700",
    gray: "text-text-primary",
  };
  return (
    <div className="rounded-lg border border-border bg-bg-card p-3 shadow-sm">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="h-3.5 w-3.5 text-text-secondary" aria-hidden="true" />
        <span className="text-xs font-medium text-text-secondary">{label}</span>
      </div>
      <p className={`text-base font-semibold tabular-nums ${textColors[color] ?? textColors.gray}`}>
        {formatMoney(value)}
      </p>
    </div>
  );
}
