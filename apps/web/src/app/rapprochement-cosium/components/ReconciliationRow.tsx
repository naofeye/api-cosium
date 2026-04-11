import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { formatMoney } from "@/lib/format";
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import type { ReconciliationListItem, CustomerReconciliation } from "./types";
import { CONFIDENCE_COLORS } from "./types";

function ExpandedDetail({ detail }: { detail: CustomerReconciliation }) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-white p-3">
        <p className="text-sm text-text-primary">{detail.explanation}</p>
      </div>

      {detail.anomalies.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <h4 className="text-sm font-semibold text-red-800 mb-2">
            Anomalies detectees ({detail.anomalies.length})
          </h4>
          <ul className="space-y-1">
            {detail.anomalies.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
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

      {detail.invoices.length > 0 && (
        <div className="rounded-lg border border-border bg-white overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-gray-50">
                <th scope="col" className="px-3 py-2 text-left font-medium text-text-secondary">Facture</th>
                <th scope="col" className="px-3 py-2 text-left font-medium text-text-secondary">Statut</th>
                <th scope="col" className="px-3 py-2 text-right font-medium text-text-secondary">TTC</th>
                <th scope="col" className="px-3 py-2 text-right font-medium text-text-secondary">Paye</th>
                <th scope="col" className="px-3 py-2 text-right font-medium text-text-secondary">Secu</th>
                <th scope="col" className="px-3 py-2 text-right font-medium text-text-secondary">Mutuelle</th>
                <th scope="col" className="px-3 py-2 text-right font-medium text-text-secondary">Client</th>
                <th scope="col" className="px-3 py-2 text-right font-medium text-text-secondary">Reste du</th>
                <th scope="col" className="px-3 py-2 text-center font-medium text-text-secondary">Paiements</th>
              </tr>
            </thead>
            <tbody>
              {detail.invoices.map((inv) => (
                <tr key={inv.invoice_id} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 font-mono font-medium">{inv.invoice_number}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={inv.status} />
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatMoney(inv.total_ti)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatMoney(inv.total_paid)}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-text-secondary">{formatMoney(inv.paid_secu)}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-text-secondary">{formatMoney(inv.paid_mutuelle)}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-text-secondary">{formatMoney(inv.paid_client)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    <span className={inv.outstanding_balance > 0.01 ? "text-red-600 font-semibold" : "text-emerald-600"}>
                      {formatMoney(inv.outstanding_balance)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center tabular-nums">{inv.payments.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

interface ReconciliationRowProps {
  item: ReconciliationListItem;
  isExpanded: boolean;
  onToggle: () => void;
  detail: CustomerReconciliation | null;
  detailLoading: boolean;
}

export function ReconciliationRow({
  item,
  isExpanded,
  onToggle,
  detail,
  detailLoading,
}: ReconciliationRowProps) {
  const resteDu = item.total_outstanding;

  return (
    <>
      <tr
        className={`border-b border-border last:border-0 transition-colors cursor-pointer ${
          isExpanded ? "bg-blue-50/40" : "hover:bg-gray-50"
        }`}
        onClick={onToggle}
      >
        <td className="px-3 py-3">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-text-secondary" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-4 w-4 text-text-secondary" aria-hidden="true" />
          )}
        </td>
        <td className="px-4 py-3">
          <Link
            href={`/clients/${item.customer_id}`}
            onClick={(e) => e.stopPropagation()}
            className="font-medium text-primary hover:underline"
          >
            {item.customer_name}
          </Link>
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={item.status} />
        </td>
        <td className="px-4 py-3">
          <span className={`inline-flex items-center text-xs font-medium rounded-full px-2.5 py-0.5 ${CONFIDENCE_COLORS[item.confidence] ?? "bg-gray-100 text-gray-700"}`}>
            {item.confidence}
          </span>
        </td>
        <td className="px-4 py-3 text-right">
          <MoneyDisplay amount={item.total_facture} />
        </td>
        <td className="px-4 py-3 text-right">
          <MoneyDisplay amount={item.total_paid} colored />
        </td>
        <td className="px-4 py-3 text-right">
          <span className={`font-semibold tabular-nums ${resteDu > 0.01 ? "text-red-600" : "text-emerald-600"}`}>
            {formatMoney(resteDu)}
          </span>
        </td>
        <td className="px-4 py-3 text-right tabular-nums text-text-secondary">
          {formatMoney(item.total_secu)}
        </td>
        <td className="px-4 py-3 text-right tabular-nums text-text-secondary">
          {formatMoney(item.total_mutuelle)}
        </td>
        <td className="px-4 py-3 text-right tabular-nums text-text-secondary">
          {formatMoney(item.total_client)}
        </td>
        <td className="px-4 py-3 text-center tabular-nums">
          {item.invoice_count}
        </td>
        <td className="px-4 py-3 text-center">
          <Link
            href={`/clients/${item.customer_id}?tab=rapprochement`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            title="Voir le detail"
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            Detail
          </Link>
        </td>
      </tr>

      {isExpanded && (
        <tr>
          <td colSpan={12} className="px-6 py-4 bg-gray-50/50">
            {detailLoading ? (
              <div className="flex items-center gap-2 text-sm text-text-secondary py-4">
                <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
                Chargement du detail...
              </div>
            ) : detail ? (
              <ExpandedDetail detail={detail} />
            ) : (
              <p className="text-sm text-text-secondary">Impossible de charger le detail.</p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
