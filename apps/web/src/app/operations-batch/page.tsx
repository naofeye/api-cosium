"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import Link from "next/link";
import { PageLayout } from "@/components/layout/PageLayout";
import { fetchJson, API_BASE } from "@/lib/api";
import type { MarketingCode, BatchSummary } from "@/lib/types";
import { History } from "lucide-react";

import { BatchSelectStep } from "./components/BatchSelectStep";
import { BatchOverviewStep } from "./components/BatchOverviewStep";
import { BatchResultsStep } from "./components/BatchResultsStep";

type Step = "select" | "overview" | "processing" | "results";

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

      {step === "select" && (
        <BatchSelectStep
          marketingCodes={marketingCodes}
          codesLoading={codesLoading}
          codesError={codesError}
          selectedCode={selectedCode}
          operationLabel={operationLabel}
          creating={creating}
          onSelectCode={setSelectedCode}
          onChangeLabel={setOperationLabel}
          onCreateBatch={handleCreateBatch}
        />
      )}

      {step === "overview" && batchSummary && (
        <BatchOverviewStep
          batchSummary={batchSummary}
          processing={processing}
          onProcess={handleProcess}
          onBack={() => {
            setStep("select");
            setBatchSummary(null);
          }}
        />
      )}

      {step === "processing" && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="mt-4 text-sm text-text-secondary">
            Traitement en cours... Veuillez patienter.
          </p>
        </div>
      )}

      {step === "results" && batchSummary && (
        <BatchResultsStep
          batchSummary={batchSummary}
          filterTab={filterTab}
          onFilterChange={setFilterTab}
          preparingPec={preparingPec}
          pecPreparedCount={pecPreparedCount}
          onPreparePec={handlePreparePec}
          onExport={handleExport}
        />
      )}
    </PageLayout>
  );
}
