"use client";

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fetchJson } from "@/lib/api";
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

export default function BatchDetailPage() {
  const params = useParams();
  const batchId = params.id as string;
  const [filterTab, setFilterTab] = useState<string>("all");
  const [preparingPec, setPreparingPec] = useState(false);
  const [pecPreparedCount, setPecPreparedCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    data: batchSummary,
    error: fetchError,
    isLoading,
  } = useSWR<BatchSummary>(`/batch/${batchId}`);

  const handlePreparePec = useCallback(async () => {
    setPreparingPec(true);
    setError(null);
    try {
      const result = await fetchJson<{ pec_prepared: number }>(
        `/batch/${batchId}/prepare-pec`,
        { method: "POST" }
      );
      setPecPreparedCount(result.pec_prepared);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors de la preparation des PEC."
      );
    } finally {
      setPreparingPec(false);
    }
  }, [batchId]);

  const handleExport = useCallback(async () => {
    try {
      const API_BASE =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
      const response = await fetch(`${API_BASE}/batch/${batchId}/export`, {
        credentials: "include",
      });
      if (!response.ok) throw new Error("Erreur export");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `batch_${batchId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError("Impossible de telecharger le fichier.");
    }
  }, [batchId]);

  if (isLoading) {
    return (
      <PageLayout
        title="Lot OptiSante"
        breadcrumb={[
          { label: "OptiSante", href: "/optisante" },
          { label: "Historique", href: "/optisante/historique" },
          { label: `Lot #${batchId}` },
        ]}
      >
        <LoadingState text="Chargement du lot..." />
      </PageLayout>
    );
  }

  if (fetchError || !batchSummary) {
    return (
      <PageLayout
        title="Lot OptiSante"
        breadcrumb={[
          { label: "OptiSante", href: "/optisante" },
          { label: "Historique", href: "/optisante/historique" },
          { label: `Lot #${batchId}` },
        ]}
      >
        <ErrorState
          message="Impossible de charger ce lot."
          onRetry={() => window.location.reload()}
        />
      </PageLayout>
    );
  }

  const { batch, items } = batchSummary;

  const filteredItems: BatchItem[] =
    filterTab === "all"
      ? items
      : items.filter((item) => item.status === filterTab);

  return (
    <PageLayout
      title={`Lot #${batch.id} — ${batch.marketing_code}`}
      description={batch.label || undefined}
      breadcrumb={[
        { label: "OptiSante", href: "/optisante" },
        { label: "Historique", href: "/optisante/historique" },
        { label: `Lot #${batch.id}` },
      ]}
    >
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-3 text-red-900 underline hover:no-underline"
          >
            Fermer
          </button>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <KPICard icon={Users} label="Total clients" value={batch.total_clients} color="info" />
        <KPICard icon={CheckCircle} label="Prets" value={batch.clients_prets} color="success" />
        <KPICard icon={AlertTriangle} label="Incomplets" value={batch.clients_incomplets} color="warning" />
        <KPICard icon={AlertOctagon} label="En conflit" value={batch.clients_en_conflit} color="danger" />
        <KPICard icon={XCircle} label="Erreurs" value={batch.clients_erreur} />
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-2 border-b border-border pb-2 mb-4">
        {ITEM_STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilterTab(tab.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              filterTab === tab.key
                ? "bg-blue-600 text-white"
                : "text-text-secondary hover:bg-gray-100"
            }`}
          >
            {tab.label}
            {tab.key !== "all" && (
              <span className="ml-1 text-xs">
                ({items.filter((i) => i.status === tab.key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Results table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-white shadow-sm mb-6">
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
                <tr
                  key={item.id}
                  className="border-b border-border last:border-0 hover:bg-gray-50"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/clients/${item.customer_id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
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
                      <Link
                        href="/pec-dashboard"
                        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                      >
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
        {batch.clients_prets > 0 && pecPreparedCount === null && (
          <button
            onClick={handlePreparePec}
            disabled={preparingPec}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
            {preparingPec ? "Preparation en cours..." : "Preparer toutes les PEC"}
          </button>
        )}

        <button
          onClick={handleExport}
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-text-primary hover:bg-gray-50 transition-colors"
        >
          <FileDown className="h-4 w-4" aria-hidden="true" />
          Exporter Excel
        </button>
      </div>

      {/* PEC summary */}
      {pecPreparedCount !== null && (
        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-6 w-6 text-emerald-600" aria-hidden="true" />
            <div>
              <p className="font-semibold text-emerald-900">
                {pecPreparedCount} fiches PEC preparees sur {batch.total_clients} dossiers
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
    </PageLayout>
  );
}
