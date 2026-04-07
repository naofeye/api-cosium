"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { fetchJson } from "@/lib/api";
import { ArrowLeftRight, RefreshCw, Link2, Search } from "lucide-react";

import type {
  ReconciliationSummary,
  ReconciliationListResponse,
  CustomerReconciliation,
  FilterTab,
} from "./components/types";
import { FILTER_TABS } from "./components/types";
import { ReconciliationStatsPanel } from "./components/ReconciliationStatsPanel";
import { ReconciliationRow } from "./components/ReconciliationRow";

export default function RapprochementCosiumPage() {
  const [activeTab, setActiveTab] = useState<FilterTab>("tous");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [linking, setLinking] = useState(false);

  const statusParam = activeTab === "tous" ? "" : `&status=${activeTab}`;
  const searchParam = searchQuery ? `&search=${encodeURIComponent(searchQuery)}` : "";

  const { data: summary, error: summaryError, mutate: mutateSummary } = useSWR<ReconciliationSummary>(
    "/reconciliation/summary",
  );

  const {
    data: listData,
    error: listError,
    isLoading: listLoading,
    mutate: mutateList,
  } = useSWR<ReconciliationListResponse>(
    `/reconciliation/list?page=${page}&page_size=${pageSize}${statusParam}${searchParam}`,
  );

  const {
    data: detailData,
    isLoading: detailLoading,
  } = useSWR<CustomerReconciliation>(
    expandedRow ? `/reconciliation/customer/${expandedRow}` : null,
  );

  const items = listData?.items ?? [];
  const total = listData?.total ?? 0;
  const error = summaryError || listError;

  const handleRunReconciliation = async () => {
    setRunning(true);
    try {
      await fetchJson("/reconciliation/link-payments", { method: "POST" });
      await fetchJson("/reconciliation/run", { method: "POST" });
      mutateSummary();
      mutateList();
    } catch {
      // Error toast handled by global handler
    } finally {
      setRunning(false);
    }
  };

  const handleLinkPayments = async () => {
    setLinking(true);
    try {
      await fetchJson("/reconciliation/link-payments", { method: "POST" });
      mutateSummary();
      mutateList();
    } catch {
      // Error toast handled by global handler
    } finally {
      setLinking(false);
    }
  };

  const toggleRow = (customerId: number) => {
    setExpandedRow((prev) => (prev === customerId ? null : customerId));
  };

  return (
    <PageLayout
      title="Rapprochement Cosium"
      description="Analyse des paiements et factures synchronises depuis Cosium"
      breadcrumb={[{ label: "Finance" }, { label: "Rapprochement Cosium" }]}
      actions={
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleLinkPayments} disabled={linking}>
            <Link2 className={`h-4 w-4 mr-1.5 ${linking ? "animate-spin" : ""}`} />
            {linking ? "Liaison..." : "Lier les paiements"}
          </Button>
          <Button onClick={handleRunReconciliation} disabled={running}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${running ? "animate-spin" : ""}`} />
            {running ? "Rapprochement en cours..." : "Lancer le rapprochement"}
          </Button>
        </div>
      }
    >
      <ReconciliationStatsPanel summary={summary} />

      {/* Filter tabs + search */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex gap-0 overflow-x-auto border border-border rounded-lg bg-bg-card">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setActiveTab(tab.key); setPage(1); }}
              className={`px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? "bg-primary text-white"
                  : "text-text-secondary hover:bg-gray-50"
              } ${tab.key === "tous" ? "rounded-l-lg" : ""} ${tab.key === "incoherent" ? "rounded-r-lg" : ""}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" aria-hidden="true" />
          <input
            type="text"
            placeholder="Rechercher un client..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            className="w-full rounded-lg border border-border pl-10 pr-4 py-2 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
            aria-label="Rechercher un client"
          />
        </div>
      </div>

      {/* Data table */}
      {listLoading ? (
        <LoadingState text="Chargement des rapprochements..." />
      ) : error ? (
        <ErrorState
          message={error?.message ?? "Erreur lors du chargement"}
          onRetry={() => { mutateSummary(); mutateList(); }}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="Aucun rapprochement"
          description="Lancez le rapprochement pour analyser les paiements et factures Cosium."
          icon={ArrowLeftRight}
          action={
            <Button onClick={handleRunReconciliation} disabled={running}>
              {running ? "En cours..." : "Lancer le rapprochement"}
            </Button>
          }
        />
      ) : (
        <>
          <div className="rounded-xl border border-border bg-bg-card shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50">
                  <th scope="col" className="w-8 px-3 py-3" />
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Client</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Statut</th>
                  <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Confiance</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Total facture</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Total paye</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Reste du</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Secu</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Mutuelle</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Client</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Factures</th>
                  <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isExpanded = expandedRow === item.customer_id;
                  return (
                    <ReconciliationRow
                      key={item.customer_id}
                      item={item}
                      isExpanded={isExpanded}
                      onToggle={() => toggleRow(item.customer_id)}
                      detail={isExpanded ? detailData ?? null : null}
                      detailLoading={isExpanded && detailLoading}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4">
            <Pagination
              total={total}
              page={page}
              pageSize={pageSize}
              onChange={setPage}
            />
          </div>
        </>
      )}
    </PageLayout>
  );
}
