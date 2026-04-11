import Link from "next/link";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { BatchSummary, BatchItem } from "@/lib/types";
import {
  Users,
  CheckCircle,
  AlertTriangle,
  AlertOctagon,
  XCircle,
  FileDown,
  ClipboardCheck,
} from "lucide-react";

const ITEM_STATUS_TABS = [
  { key: "all", label: "Tous" },
  { key: "pret", label: "Prets" },
  { key: "incomplet", label: "Incomplets" },
  { key: "conflit", label: "Conflits" },
  { key: "erreur", label: "Erreurs" },
] as const;

function CompletionBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(score)));
  const color =
    pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 rounded-full bg-gray-200">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-text-secondary tabular-nums">{pct}%</span>
    </div>
  );
}

interface BatchResultsStepProps {
  batchSummary: BatchSummary;
  filterTab: string;
  onFilterChange: (tab: string) => void;
  preparingPec: boolean;
  pecPreparedCount: number | null;
  onPreparePec: () => void;
  onExport: () => void;
}

export function BatchResultsStep({
  batchSummary,
  filterTab,
  onFilterChange,
  preparingPec,
  pecPreparedCount,
  onPreparePec,
  onExport,
}: BatchResultsStepProps) {
  const filteredItems: BatchItem[] =
    filterTab === "all"
      ? batchSummary.items
      : batchSummary.items.filter((item) => item.status === filterTab);

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard icon={Users} label="Total clients" value={batchSummary.batch.total_clients} color="info" />
        <KPICard icon={CheckCircle} label="Prets" value={batchSummary.batch.clients_prets} color="success" />
        <KPICard icon={AlertTriangle} label="Incomplets" value={batchSummary.batch.clients_incomplets} color="warning" />
        <KPICard icon={AlertOctagon} label="En conflit" value={batchSummary.batch.clients_en_conflit} color="danger" />
        <KPICard icon={XCircle} label="Erreurs" value={batchSummary.batch.clients_erreur} />
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-2 border-b border-border pb-2">
        {ITEM_STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onFilterChange(tab.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              filterTab === tab.key
                ? "bg-blue-600 text-white"
                : "text-text-secondary hover:bg-gray-100"
            }`}
          >
            {tab.label}
            {tab.key !== "all" && (
              <span className="ml-1 text-xs">
                ({batchSummary.items.filter((i) => i.status === tab.key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Results table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-gray-50 text-left">
              <th className="px-4 py-3 font-medium text-text-secondary">Client</th>
              <th className="px-4 py-3 font-medium text-text-secondary">Statut</th>
              <th className="px-4 py-3 font-medium text-text-secondary">Completude</th>
              <th className="px-4 py-3 font-medium text-text-secondary">Erreurs</th>
              <th className="px-4 py-3 font-medium text-text-secondary">Alertes</th>
              <th className="px-4 py-3 font-medium text-text-secondary">Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                  Aucun element dans cette categorie.
                </td>
              </tr>
            ) : (
              filteredItems.map((item) => (
                <tr key={item.id} className="border-b border-border last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/clients/${item.customer_id}`} className="font-medium text-blue-600 hover:underline">
                      {item.customer_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3">
                    <CompletionBar score={item.completude_score} />
                  </td>
                  <td className="px-4 py-3 tabular-nums">
                    {item.errors_count > 0 ? (
                      <span className="text-red-600 font-medium">{item.errors_count}</span>
                    ) : (
                      <span className="text-text-secondary">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3 tabular-nums">
                    {item.warnings_count > 0 ? (
                      <span className="text-amber-600 font-medium">{item.warnings_count}</span>
                    ) : (
                      <span className="text-text-secondary">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {item.pec_preparation_id ? (
                      <Link href="/pec-dashboard" className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline">
                        Voir PEC
                      </Link>
                    ) : (
                      <span className="text-text-secondary text-xs">-</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-3">
        {batchSummary.batch.clients_prets > 0 && pecPreparedCount === null && (
          <button
            onClick={onPreparePec}
            disabled={preparingPec}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
            {preparingPec ? "Preparation en cours..." : "Preparer toutes les PEC"}
          </button>
        )}

        <button
          onClick={onExport}
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-text-primary hover:bg-gray-50 transition-colors"
        >
          <FileDown className="h-4 w-4" aria-hidden="true" />
          Exporter Excel
        </button>
      </div>

      {/* PEC summary */}
      {pecPreparedCount !== null && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-6 w-6 text-emerald-600" aria-hidden="true" />
            <div>
              <p className="font-semibold text-emerald-900">
                {pecPreparedCount} fiches PEC preparees sur {batchSummary.batch.total_clients} dossiers
              </p>
              <Link
                href="/pec-dashboard"
                className="mt-1 inline-block text-sm text-emerald-700 hover:underline"
              >
                Voir le tableau de bord PEC
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
