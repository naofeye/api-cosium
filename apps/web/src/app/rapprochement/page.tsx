"use client";

import { useState, useMemo } from "react";
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
import { formatMoney } from "@/lib/format";
import { ManualReconciliation } from "./components/ManualReconciliation";
import {
  Upload,
  RefreshCw,
  Link2,
  CheckCircle,
  AlertCircle,
  FileText,
  BarChart3,
  Calendar,
} from "lucide-react";

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

  /* Date range filter */
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const buildSwrKey = () => {
    const parts: string[] = [];
    if (showReconciled !== undefined) parts.push(`reconciled=${showReconciled}`);
    if (dateFrom) parts.push(`date_from=${dateFrom}`);
    if (dateTo) parts.push(`date_to=${dateTo}`);
    const qs = parts.length > 0 ? `?${parts.join("&")}` : "";
    return `/banking/transactions${qs}`;
  };

  const swrKey = buildSwrKey();
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

  /* ─── KPI computations ─── */
  const { matchedCount, unmatchedCount, unmatchedTx, tauxRapprochement, totalImported, totalMatched, totalUnmatched } =
    useMemo(() => {
      const matched = transactions.filter((t) => t.reconciled);
      const unmatched = transactions.filter((t) => !t.reconciled);
      const taux = total > 0 ? Math.round((matched.length / total) * 100) : 0;
      const totalM = matched.reduce((s, t) => s + Math.abs(t.montant), 0);
      const totalU = unmatched.reduce((s, t) => s + Math.abs(t.montant), 0);
      return {
        matchedCount: matched.length,
        unmatchedCount: unmatched.length,
        unmatchedTx: unmatched,
        tauxRapprochement: taux,
        totalImported: total,
        totalMatched: totalM,
        totalUnmatched: totalU,
      };
    }, [transactions, total]);

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
      await mutate();
      await mutatePayments();
      setReconcileResult(`${resp.matched} rapproche(s), ${resp.unmatched} non rapproche(s)`);
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
      await mutate();
      await mutatePayments();
      setMatchResult("Transaction rapprochee avec succes");
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
      {/* KPI Bar */}
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

      {/* Mini summary amounts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Montant rapproche</p>
            <p className="text-lg font-bold tabular-nums text-emerald-700">{formatMoney(totalMatched)}</p>
          </div>
          <CheckCircle className="h-8 w-8 text-emerald-200" />
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Montant non rapproche</p>
            <p className="text-lg font-bold tabular-nums text-amber-700">{formatMoney(totalUnmatched)}</p>
          </div>
          <AlertCircle className="h-8 w-8 text-amber-200" />
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Paiements a rapprocher</p>
            <p className="text-lg font-bold tabular-nums text-blue-700">{payments.length}</p>
          </div>
          <Link2 className="h-8 w-8 text-blue-200" />
        </div>
      </div>

      {/* Action bar + filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
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

        <div className="h-6 w-px bg-gray-200 mx-1" />

        {/* Reconciled filter */}
        <label htmlFor="filter-reconciled" className="sr-only">Filtrer par statut de rapprochement</label>
        <select
          id="filter-reconciled"
          value={showReconciled === undefined ? "" : String(showReconciled)}
          onChange={(e) => setShowReconciled(e.target.value === "" ? undefined : e.target.value === "true")}
          className="rounded-lg border border-border px-3 py-2 text-sm"
          aria-label="Filtrer par statut de rapprochement"
        >
          <option value="">Toutes</option>
          <option value="false">Non rapprochees</option>
          <option value="true">Rapprochees</option>
        </select>

        {/* Date range filter */}
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-text-secondary" />
          <label htmlFor="date-from" className="sr-only">Date debut</label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
            aria-label="Date debut"
          />
          <span className="text-text-secondary text-sm">au</span>
          <label htmlFor="date-to" className="sr-only">Date fin</label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
            aria-label="Date fin"
          />
          {(dateFrom || dateTo) && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setDateFrom("");
                setDateTo("");
              }}
            >
              Effacer
            </Button>
          )}
        </div>
      </div>

      {/* Result banners */}
      {importResult && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" aria-hidden="true" /> {importResult}
        </div>
      )}
      {reconcileResult && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700 flex items-center gap-2">
          <Link2 className="h-4 w-4" aria-hidden="true" /> {reconcileResult}
        </div>
      )}
      {matchResult && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" aria-hidden="true" /> {matchResult}
        </div>
      )}
      {matching && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700 flex items-center gap-2">
          <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" /> Rapprochement en cours...
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
        <EmptyState
          title="Aucune transaction bancaire"
          description="Importez un releve CSV depuis votre banque pour commencer le rapprochement."
          icon={FileText}
          action={
            <label className="cursor-pointer">
              <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover transition-colors">
                <Upload className="h-4 w-4" />
                Importer un releve CSV
              </span>
            </label>
          }
        />
      ) : (
        <>
          {/* Side-by-side manual reconciliation zone */}
          <ManualReconciliation unmatchedTx={unmatchedTx} payments={payments} onMatch={handleManualMatch} />

          {/* Full transaction table with color coding */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Toutes les transactions</h2>
            <div className="rounded-xl border border-border bg-bg-card shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-gray-50">
                    <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
                    <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Libelle</th>
                    <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Montant</th>
                    <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Reference</th>
                    <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr
                      key={tx.id}
                      className={`border-b border-border last:border-0 transition-colors ${
                        tx.reconciled
                          ? "bg-emerald-50/40 hover:bg-emerald-50"
                          : "bg-amber-50/30 hover:bg-amber-50"
                      }`}
                    >
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
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-100 rounded-full px-2.5 py-0.5">
                            <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" /> Rapprochee
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-100 rounded-full px-2.5 py-0.5">
                            <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" /> Non rapprochee
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
