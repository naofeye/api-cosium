"use client";

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { fetchJson, API_BASE } from "@/lib/api";
import type { BatchSummary, BatchItem } from "@/lib/types";
import { BatchItemsTable } from "./components/BatchItemsTable";
import { BatchActions } from "./components/BatchActions";
import {
  Users,
  CheckCircle,
  AlertTriangle,
  AlertOctagon,
  XCircle,
} from "lucide-react";

const ITEM_STATUS_TABS = [
  { key: "all", label: "Tous" },
  { key: "pret", label: "Prets" },
  { key: "incomplet", label: "Incomplets" },
  { key: "conflit", label: "Conflits" },
  { key: "erreur", label: "Erreurs" },
] as const;

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

  const breadcrumb = [
    { label: "Groupes marketing", href: "/operations-batch" },
    { label: "Historique", href: "/operations-batch/historique" },
    { label: `Lot #${batchId}` },
  ];

  if (isLoading) {
    return (
      <PageLayout title="Lot operations" breadcrumb={breadcrumb}>
        <LoadingState text="Chargement du lot..." />
      </PageLayout>
    );
  }

  if (fetchError || !batchSummary) {
    return (
      <PageLayout title="Lot operations" breadcrumb={breadcrumb}>
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
        { label: "Groupes marketing", href: "/operations-batch" },
        { label: "Historique", href: "/operations-batch/historique" },
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

      <BatchItemsTable items={filteredItems} />

      <BatchActions
        clientsPrets={batch.clients_prets}
        totalClients={batch.total_clients}
        pecPreparedCount={pecPreparedCount}
        preparingPec={preparingPec}
        onPreparePec={handlePreparePec}
        onExport={handleExport}
      />
    </PageLayout>
  );
}
