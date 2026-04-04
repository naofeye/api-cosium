"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { KPICard } from "@/components/ui/KPICard";
import { fetchJson } from "@/lib/api";
import { DraggableTransaction } from "./components/DraggableTransaction";
import { DroppablePayment } from "./components/DroppablePayment";
import { Upload, RefreshCw, Link2, CheckCircle, AlertCircle, FileText, GripVertical } from "lucide-react";

interface BankTx {
  id: number;
  date: string;
  libelle: string;
  montant: number;
  reference: string | null;
  reconciled: boolean;
  reconciled_payment_id: number | null;
}

interface TxList {
  items: BankTx[];
  total: number;
}

interface PaymentItem {
  id: number;
  case_id: number;
  payer_type: string;
  mode_paiement: string | null;
  reference_externe: string | null;
  date_paiement: string | null;
  amount_due: number;
  amount_paid: number;
  status: string;
}

export default function RapprochementPage() {
  const [uploading, setUploading] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [matching, setMatching] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [reconcileResult, setReconcileResult] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<string | null>(null);
  const [showReconciled, setShowReconciled] = useState<boolean | undefined>(undefined);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const swrKey = `/banking/transactions${showReconciled !== undefined ? `?reconciled=${showReconciled}` : ""}`;
  const { data: txData, error: swrError, isLoading, mutate } = useSWR<TxList>(swrKey);

  const {
    data: unreconciledPayments,
    isLoading: paymentsLoading,
    mutate: mutatePayments,
  } = useSWR<PaymentItem[]>("/banking/unreconciled-payments");

  const transactions = txData?.items ?? [];
  const total = txData?.total ?? 0;
  const payments = unreconciledPayments ?? [];
  const error = swrError?.message ?? mutationError ?? null;

  const unmatchedTx = transactions.filter((t) => !t.reconciled);
  const matchedCount = transactions.filter((t) => t.reconciled).length;
  const unmatchedCount = unmatchedTx.length;

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setImportResult(null);
    setMutationError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await fetchJson<{ imported?: number; total?: number }>("/banking/import-statement", {
        method: "POST",
        body: formData,
      });
      setImportResult(`${data.imported ?? data.total ?? 0} transaction(s) importee(s)`);
      mutate();
    } catch {
      setMutationError("Erreur lors de l'import");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const autoReconcile = async () => {
    setReconciling(true);
    setReconcileResult(null);
    setMutationError(null);
    try {
      const resp = await fetchJson<{ matched: number; unmatched: number }>("/banking/reconcile", { method: "POST" });
      setReconcileResult(`${resp.matched} rapproche(s), ${resp.unmatched} non rapproche(s)`);
      mutate();
      mutatePayments();
    } catch {
      setMutationError("Erreur lors du rapprochement");
    } finally {
      setReconciling(false);
    }
  };

  const handleManualMatch = async (transactionId: number, paymentId: number) => {
    setMatching(true);
    setMatchResult(null);
    setMutationError(null);
    try {
      await fetchJson("/banking/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transaction_id: transactionId, payment_id: paymentId }),
      });
      setMatchResult("Transaction rapprochee avec succes");
      mutate();
      mutatePayments();
    } catch {
      setMutationError("Erreur lors du rapprochement manuel");
    } finally {
      setMatching(false);
    }
  };

  return (
    <PageLayout
      title="Rapprochement bancaire"
      description="Import de releves et rapprochement avec les paiements"
      breadcrumb={[{ label: "Rapprochement" }]}
    >
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KPICard icon={FileText} label="Total transactions" value={total} color="primary" />
        <KPICard icon={CheckCircle} label="Rapprochees" value={matchedCount} color="success" />
        <KPICard
          icon={AlertCircle}
          label="Non rapprochees"
          value={unmatchedCount}
          color={unmatchedCount > 0 ? "danger" : "success"}
        />
        <KPICard
          icon={Link2}
          label="Paiements a rapprocher"
          value={payments.length}
          color={payments.length > 0 ? "warning" : "success"}
        />
      </div>

      <div className="flex items-center gap-3 mb-6">
        <label className="cursor-pointer">
          <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-card px-4 py-2 text-sm font-medium hover:bg-gray-50 transition-colors">
            <Upload className="h-4 w-4" />
            {uploading ? "Import en cours..." : "Importer un releve CSV"}
          </span>
        </label>
        <Button variant="outline" onClick={autoReconcile} disabled={reconciling}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${reconciling ? "animate-spin" : ""}`} />
          {reconciling ? "Rapprochement..." : "Rapprochement auto"}
        </Button>
        <select
          value={showReconciled === undefined ? "" : String(showReconciled)}
          onChange={(e) => setShowReconciled(e.target.value === "" ? undefined : e.target.value === "true")}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="">Toutes</option>
          <option value="false">Non rapprochees</option>
          <option value="true">Rapprochees</option>
        </select>
      </div>

      {importResult && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" /> {importResult}
        </div>
      )}
      {reconcileResult && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700 flex items-center gap-2">
          <Link2 className="h-4 w-4" /> {reconcileResult}
        </div>
      )}
      {matchResult && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" /> {matchResult}
        </div>
      )}

      {matching && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700 flex items-center gap-2">
          <RefreshCw className="h-4 w-4 animate-spin" /> Rapprochement en cours...
        </div>
      )}

      {isLoading || paymentsLoading ? (
        <LoadingState text="Chargement des transactions et paiements..." />
      ) : error ? (
        <ErrorState
          message={error}
          onRetry={() => {
            mutate();
            mutatePayments();
          }}
        />
      ) : transactions.length === 0 && payments.length === 0 ? (
        <EmptyState title="Aucune transaction" description="Importez un releve CSV pour commencer le rapprochement." />
      ) : (
        <>
          {/* Drag-and-drop zone for unmatched items */}
          {(unmatchedTx.length > 0 || payments.length > 0) && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-3">
                <GripVertical className="h-4 w-4 text-gray-400" aria-hidden="true" />
                <h2 className="text-lg font-semibold text-gray-800">Rapprochement manuel</h2>
              </div>
              <p className="text-sm text-gray-500 mb-4">Glissez une transaction sur un paiement pour les rapprocher.</p>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left column: Unmatched transactions */}
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                    Transactions non rapprochees ({unmatchedTx.length})
                  </h3>
                  {unmatchedTx.length === 0 ? (
                    <div className="border border-dashed border-border rounded-lg p-6 text-center text-sm text-gray-400">
                      Toutes les transactions sont rapprochees
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                      {unmatchedTx.map((tx) => (
                        <DraggableTransaction key={tx.id} id={tx.id}>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 min-w-0">
                              <GripVertical
                                className="h-4 w-4 text-gray-300 flex-shrink-0"
                                aria-label="Glisser pour rapprocher"
                              />
                              <div className="min-w-0">
                                <p className="text-sm font-medium truncate">{tx.libelle}</p>
                                <p className="text-xs text-gray-500">
                                  <DateDisplay date={tx.date} />
                                  {tx.reference && <span className="ml-2 font-mono">{tx.reference}</span>}
                                </p>
                              </div>
                            </div>
                            <MoneyDisplay amount={tx.montant} colored />
                          </div>
                        </DraggableTransaction>
                      ))}
                    </div>
                  )}
                </div>

                {/* Right column: Unreconciled payments */}
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                    <Link2 className="h-4 w-4 text-blue-500" />
                    Paiements a rapprocher ({payments.length})
                  </h3>
                  {payments.length === 0 ? (
                    <div className="border border-dashed border-border rounded-lg p-6 text-center text-sm text-gray-400">
                      Aucun paiement en attente de rapprochement
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                      {payments.map((p) => (
                        <DroppablePayment key={p.id} id={p.id} onMatch={handleManualMatch}>
                          <div className="flex items-center justify-between">
                            <div className="min-w-0">
                              <p className="text-sm font-medium">
                                Paiement #{p.id}
                                <span className="ml-2 text-xs text-gray-500">{p.payer_type}</span>
                              </p>
                              <p className="text-xs text-gray-500">
                                {p.date_paiement && <DateDisplay date={p.date_paiement} />}
                                {p.mode_paiement && <span className="ml-2">{p.mode_paiement}</span>}
                                {p.reference_externe && <span className="ml-2 font-mono">{p.reference_externe}</span>}
                              </p>
                            </div>
                            <MoneyDisplay amount={p.amount_paid} colored />
                          </div>
                        </DroppablePayment>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Full transaction table */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Toutes les transactions</h2>
            <div className="rounded-xl border border-border bg-bg-card shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-gray-50">
                    <th className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
                    <th className="px-4 py-3 text-left font-medium text-text-secondary">Libelle</th>
                    <th className="px-4 py-3 text-right font-medium text-text-secondary">Montant</th>
                    <th className="px-4 py-3 text-left font-medium text-text-secondary">Reference</th>
                    <th className="px-4 py-3 text-center font-medium text-text-secondary">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="border-b border-border last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <DateDisplay date={tx.date} />
                      </td>
                      <td className="px-4 py-3 font-medium max-w-xs truncate">{tx.libelle}</td>
                      <td className="px-4 py-3 text-right">
                        <MoneyDisplay amount={tx.montant} colored />
                      </td>
                      <td className="px-4 py-3 text-text-secondary font-mono text-xs">{tx.reference || "-"}</td>
                      <td className="px-4 py-3 text-center">
                        {tx.reconciled ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                            <CheckCircle className="h-3.5 w-3.5" /> Rapprochee
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700">
                            <AlertCircle className="h-3.5 w-3.5" /> Non rapprochee
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </PageLayout>
  );
}
