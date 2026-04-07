"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import Link from "next/link";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fetchJson } from "@/lib/api";
import type { MarketingCode, BatchSummary, BatchItem } from "@/lib/types";
import {
  Users,
  CheckCircle,
  AlertTriangle,
  AlertOctagon,
  XCircle,
  Play,
  FileDown,
  ClipboardCheck,
  History,
} from "lucide-react";

type Step = "select" | "overview" | "processing" | "results";

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

export default function BatchOperationsPage() {
  const [step, setStep] = useState<Step>("select");
  const [selectedCode, setSelectedCode] = useState("");
  const [operationLabel, setOperationLabel] = useState("");
  const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
  const [creating, setCreating] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [preparingPec, setPreparingPec] = useState(false);
  const [pecPreparedCount, setPecPreparedCount] = useState<number | null>(null);
  const [filterTab, setFilterTab] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);

  const {
    data: marketingCodes,
    error: codesError,
    isLoading: codesLoading,
  } = useSWR<MarketingCode[]>("/batch/marketing-codes");

  const handleCreateBatch = useCallback(async () => {
    if (!selectedCode) return;
    setCreating(true);
    setError(null);
    try {
      const result = await fetchJson<BatchSummary>("/batch/create", {
        method: "POST",
        body: JSON.stringify({
          marketing_code: selectedCode,
          label: operationLabel || undefined,
        }),
      });
      setBatchSummary(result);
      setStep("overview");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Impossible de creer le lot. Reessayez."
      );
    } finally {
      setCreating(false);
    }
  }, [selectedCode, operationLabel]);

  const handleProcess = useCallback(async () => {
    if (!batchSummary) return;
    setProcessing(true);
    setError(null);
    setStep("processing");
    try {
      const result = await fetchJson<BatchSummary>(
        `/batch/${batchSummary.batch.id}/process`,
        { method: "POST" }
      );
      setBatchSummary(result);
      setStep("results");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors du traitement. Reessayez."
      );
      setStep("overview");
    } finally {
      setProcessing(false);
    }
  }, [batchSummary]);

  const handlePreparePec = useCallback(async () => {
    if (!batchSummary) return;
    setPreparingPec(true);
    setError(null);
    try {
      const result = await fetchJson<{ pec_prepared: number }>(
        `/batch/${batchSummary.batch.id}/prepare-pec`,
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
  }, [batchSummary]);

  const handleExport = useCallback(async () => {
    if (!batchSummary) return;
    try {
      const API_BASE =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
      const response = await fetch(
        `${API_BASE}/batch/${batchSummary.batch.id}/export`,
        { credentials: "include" }
      );
      if (!response.ok) throw new Error("Erreur export");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `batch_${batchSummary.batch.id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError("Impossible de telecharger le fichier.");
    }
  }, [batchSummary]);

  const filteredItems: BatchItem[] = batchSummary
    ? filterTab === "all"
      ? batchSummary.items
      : batchSummary.items.filter((item) => item.status === filterTab)
    : [];

  return (
    <PageLayout
      title="Groupes marketing — Journees en entreprise"
      description="Traitement batch des dossiers PEC par code marketing"
      breadcrumb={[{ label: "Groupes marketing", href: "/operations-batch" }]}
      actions={
        <Link
          href="/operations-batch/historique"
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-text-primary hover:bg-gray-50 transition-colors"
        >
          <History className="h-4 w-4" aria-hidden="true" />
          Historique
        </Link>
      }
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

      {/* STEP 1: Select marketing code */}
      {step === "select" && (
        <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            1. Selectionner un code marketing
          </h2>

          {codesLoading && (
            <LoadingState text="Chargement des codes marketing..." />
          )}

          {codesError && (
            <ErrorState
              message="Impossible de charger les codes marketing."
              onRetry={() => window.location.reload()}
            />
          )}

          {!codesLoading && !codesError && marketingCodes && marketingCodes.length === 0 && (
            <EmptyState
              title="Aucun code marketing trouve"
              description="Synchronisez les tags Cosium."
            />
          )}

          {!codesLoading && !codesError && marketingCodes && marketingCodes.length > 0 && (
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="marketing-code"
                  className="block text-sm font-medium text-text-primary mb-1"
                >
                  Code marketing
                </label>
                <select
                  id="marketing-code"
                  value={selectedCode}
                  onChange={(e) => setSelectedCode(e.target.value)}
                  className="w-full max-w-md rounded-lg border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="">-- Choisir un code --</option>
                  {marketingCodes.map((mc) => (
                    <option key={mc.code} value={mc.code}>
                      {mc.description || mc.code} ({mc.client_count} clients)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="operation-label"
                  className="block text-sm font-medium text-text-primary mb-1"
                >
                  Label de l&apos;operation (optionnel)
                </label>
                <input
                  id="operation-label"
                  type="text"
                  value={operationLabel}
                  onChange={(e) => setOperationLabel(e.target.value)}
                  placeholder="Journee SAFRAN 06/04/2026"
                  className="w-full max-w-md rounded-lg border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <button
                onClick={handleCreateBatch}
                disabled={!selectedCode || creating}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {creating ? "Creation en cours..." : "Creer le lot"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* STEP 2: Batch overview */}
      {step === "overview" && batchSummary && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <KPICard
              icon={Users}
              label="Total clients"
              value={batchSummary.batch.total_clients}
              color="info"
            />
            <KPICard
              icon={CheckCircle}
              label="Prets"
              value={batchSummary.batch.clients_prets}
              color="success"
            />
            <KPICard
              icon={AlertTriangle}
              label="Incomplets"
              value={batchSummary.batch.clients_incomplets}
              color="warning"
            />
            <KPICard
              icon={AlertOctagon}
              label="En conflit"
              value={batchSummary.batch.clients_en_conflit}
              color="danger"
            />
            <KPICard
              icon={XCircle}
              label="Erreurs"
              value={batchSummary.batch.clients_erreur}
            />
          </div>

          {batchSummary.items.length === 0 ? (
            <EmptyState
              title="Aucun client trouve"
              description="Aucun client trouve pour ce code marketing."
            />
          ) : (
            <div className="flex gap-3">
              <button
                onClick={handleProcess}
                disabled={processing}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Play className="h-4 w-4" aria-hidden="true" />
                {processing ? "Traitement en cours..." : "Lancer le traitement"}
              </button>
              <button
                onClick={() => {
                  setStep("select");
                  setBatchSummary(null);
                }}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-text-primary hover:bg-gray-50 transition-colors"
              >
                Retour
              </button>
            </div>
          )}
        </div>
      )}

      {/* STEP 2b: Processing */}
      {step === "processing" && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="mt-4 text-sm text-text-secondary">
            Traitement en cours... Veuillez patienter.
          </p>
        </div>
      )}

      {/* STEP 3: Results table */}
      {step === "results" && batchSummary && (
        <div className="space-y-6">
          {/* KPIs */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <KPICard
              icon={Users}
              label="Total clients"
              value={batchSummary.batch.total_clients}
              color="info"
            />
            <KPICard
              icon={CheckCircle}
              label="Prets"
              value={batchSummary.batch.clients_prets}
              color="success"
            />
            <KPICard
              icon={AlertTriangle}
              label="Incomplets"
              value={batchSummary.batch.clients_incomplets}
              color="warning"
            />
            <KPICard
              icon={AlertOctagon}
              label="En conflit"
              value={batchSummary.batch.clients_en_conflit}
              color="danger"
            />
            <KPICard
              icon={XCircle}
              label="Erreurs"
              value={batchSummary.batch.clients_erreur}
            />
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-2 border-b border-border pb-2">
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
                {tab.key !== "all" && batchSummary && (
                  <span className="ml-1 text-xs">
                    (
                    {
                      batchSummary.items.filter((i) => i.status === tab.key)
                        .length
                    }
                    )
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
                  <th className="px-4 py-3 font-medium text-text-secondary">
                    Client
                  </th>
                  <th className="px-4 py-3 font-medium text-text-secondary">
                    Statut
                  </th>
                  <th className="px-4 py-3 font-medium text-text-secondary">
                    Completude
                  </th>
                  <th className="px-4 py-3 font-medium text-text-secondary">
                    Erreurs
                  </th>
                  <th className="px-4 py-3 font-medium text-text-secondary">
                    Alertes
                  </th>
                  <th className="px-4 py-3 font-medium text-text-secondary">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-text-secondary"
                    >
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
                          <span className="text-red-600 font-medium">
                            {item.errors_count}
                          </span>
                        ) : (
                          <span className="text-text-secondary">0</span>
                        )}
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {item.warnings_count > 0 ? (
                          <span className="text-amber-600 font-medium">
                            {item.warnings_count}
                          </span>
                        ) : (
                          <span className="text-text-secondary">0</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {item.pec_preparation_id ? (
                          <Link
                            href={`/pec-dashboard`}
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
            {batchSummary.batch.clients_prets > 0 &&
              pecPreparedCount === null && (
                <button
                  onClick={handlePreparePec}
                  disabled={preparingPec}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
                  {preparingPec
                    ? "Preparation en cours..."
                    : "Preparer toutes les PEC"}
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

          {/* Step 4: PEC summary */}
          {pecPreparedCount !== null && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-6 w-6 text-emerald-600" aria-hidden="true" />
                <div>
                  <p className="font-semibold text-emerald-900">
                    {pecPreparedCount} fiches PEC preparees sur{" "}
                    {batchSummary.batch.total_clients} dossiers
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
      )}
    </PageLayout>
  );
}
