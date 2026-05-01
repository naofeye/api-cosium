"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { CheckCircle, FileText, Link2, RefreshCw, Upload } from "lucide-react";

import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

import { ManualReconciliation } from "./components/ManualReconciliation";
import { RapprochementKPIs } from "./components/RapprochementKPIs";
import { RapprochementToolbar } from "./components/RapprochementToolbar";
import { TransactionsTable } from "./components/TransactionsTable";
import { useRapprochementActions } from "./hooks/useRapprochementActions";
import type { PaymentItem, TxList } from "./types";

function buildSwrKey(showReconciled: boolean | undefined, dateFrom: string, dateTo: string): string {
  const parts: string[] = [];
  if (showReconciled !== undefined) parts.push(`reconciled=${showReconciled}`);
  if (dateFrom) parts.push(`date_from=${dateFrom}`);
  if (dateTo) parts.push(`date_to=${dateTo}`);
  const qs = parts.length > 0 ? `?${parts.join("&")}` : "";
  return `/banking/transactions${qs}`;
}

export default function RapprochementPage() {
  const [showReconciled, setShowReconciled] = useState<boolean | undefined>(undefined);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const swrKey = buildSwrKey(showReconciled, dateFrom, dateTo);
  const { data: txData, error: swrError, isLoading, mutate: mutateTx } = useSWR<TxList>(swrKey);
  const { data: paymentsData, isLoading: paymentsLoading, mutate: mutatePayments } =
    useSWR<PaymentItem[]>("/banking/unreconciled-payments");

  // useMemo pour stabiliser les references quand SWR retourne undefined :
  // sinon kpis (qui depend de transactions) recalcule a chaque render.
  const transactions = useMemo(() => txData?.items ?? [], [txData]);
  const total = txData?.total ?? 0;
  const payments = useMemo(() => paymentsData ?? [], [paymentsData]);

  const { state, actions } = useRapprochementActions({
    refetchTx: mutateTx,
    refetchPayments: mutatePayments,
  });
  const error = swrError?.message ?? state.mutationError ?? null;

  const kpis = useMemo(() => {
    const matched = transactions.filter((t) => t.reconciled);
    const unmatched = transactions.filter((t) => !t.reconciled);
    const taux = total > 0 ? Math.round((matched.length / total) * 100) : 0;
    return {
      matchedCount: matched.length,
      unmatchedCount: unmatched.length,
      unmatchedTx: unmatched,
      tauxRapprochement: taux,
      totalImported: total,
      totalMatched: matched.reduce((s, t) => s + Math.abs(t.montant), 0),
      totalUnmatched: unmatched.reduce((s, t) => s + Math.abs(t.montant), 0),
    };
  }, [transactions, total]);

  return (
    <PageLayout
      title="Rapprochement bancaire"
      description="Import de releves et rapprochement avec les paiements"
      breadcrumb={[{ label: "Rapprochement" }]}
    >
      <RapprochementKPIs
        totalImported={kpis.totalImported}
        matchedCount={kpis.matchedCount}
        unmatchedCount={kpis.unmatchedCount}
        tauxRapprochement={kpis.tauxRapprochement}
        totalMatched={kpis.totalMatched}
        totalUnmatched={kpis.totalUnmatched}
        paymentsCount={payments.length}
      />

      <RapprochementToolbar
        uploading={state.uploading}
        reconciling={state.reconciling}
        showReconciled={showReconciled}
        dateFrom={dateFrom}
        dateTo={dateTo}
        onUpload={actions.upload}
        onAutoReconcile={actions.autoReconcile}
        onChangeReconciled={setShowReconciled}
        onChangeDateFrom={setDateFrom}
        onChangeDateTo={setDateTo}
        onClearDates={() => { setDateFrom(""); setDateTo(""); }}
      />

      {state.importResult && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" aria-hidden="true" /> {state.importResult}
        </div>
      )}
      {state.reconcileResult && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700 flex items-center gap-2">
          <Link2 className="h-4 w-4" aria-hidden="true" /> {state.reconcileResult}
        </div>
      )}
      {state.matchResult && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" aria-hidden="true" /> {state.matchResult}
        </div>
      )}
      {state.matching && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700 flex items-center gap-2">
          <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" /> Rapprochement en cours...
        </div>
      )}

      {isLoading || paymentsLoading ? (
        <LoadingState text="Chargement des transactions et paiements..." />
      ) : error ? (
        <ErrorState
          message={error}
          onRetry={() => { mutateTx(); mutatePayments(); }}
        />
      ) : transactions.length === 0 && payments.length === 0 ? (
        <EmptyState
          title="Aucune transaction bancaire"
          description="Importez un releve CSV depuis votre banque pour commencer le rapprochement."
          icon={FileText}
          action={
            <label className="cursor-pointer">
              <input type="file" accept=".csv" onChange={actions.upload} className="hidden" />
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover transition-colors">
                <Upload className="h-4 w-4" aria-hidden="true" />
                Importer un releve CSV
              </span>
            </label>
          }
        />
      ) : (
        <>
          <ManualReconciliation
            unmatchedTx={kpis.unmatchedTx}
            payments={payments}
            onMatch={actions.manualMatch}
          />
          <TransactionsTable transactions={transactions} />
        </>
      )}
    </PageLayout>
  );
}
