"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import Link from "next/link";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Pagination } from "@/components/ui/Pagination";
import { formatMoney } from "@/lib/format";
import { fetchJson } from "@/lib/api";
import {
  CheckCircle,
  AlertCircle,
  FileText,
  Users,
  Euro,
  ArrowLeftRight,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  Link2,
  Search,
} from "lucide-react";

/* ---- Types ---- */

interface ReconciliationSummary {
  total_customers: number;
  solde: number;
  solde_non_rapproche: number;
  partiellement_paye: number;
  en_attente: number;
  incoherent: number;
  info_insuffisante: number;
  total_facture: number;
  total_outstanding: number;
  total_paid: number;
}

interface ReconciliationListItem {
  customer_id: number;
  customer_name: string;
  status: string;
  confidence: string;
  total_facture: number;
  total_outstanding: number;
  total_paid: number;
  total_secu: number;
  total_mutuelle: number;
  total_client: number;
  total_avoir: number;
  invoice_count: number;
  has_pec: boolean;
  explanation: string;
  reconciled_at: string;
}

interface ReconciliationListResponse {
  items: ReconciliationListItem[];
  total: number;
  page: number;
  page_size: number;
}

interface AnomalyItem {
  type: string;
  severity: string;
  message: string;
  invoice_number?: string;
  amount?: number;
}

interface PaymentMatch {
  payment_id: number;
  amount: number;
  type: string;
  category: string;
  issuer_name: string;
}

interface InvoiceReconciliation {
  invoice_id: number;
  invoice_number: string;
  invoice_date: string | null;
  total_ti: number;
  outstanding_balance: number;
  settled: boolean;
  total_paid: number;
  paid_secu: number;
  paid_mutuelle: number;
  paid_client: number;
  paid_avoir: number;
  status: string;
  payments: PaymentMatch[];
  anomalies: AnomalyItem[];
}

interface CustomerReconciliation {
  id: number;
  customer_id: number;
  customer_name: string;
  status: string;
  confidence: string;
  total_facture: number;
  total_outstanding: number;
  total_paid: number;
  total_secu: number;
  total_mutuelle: number;
  total_client: number;
  total_avoir: number;
  invoice_count: number;
  invoices: InvoiceReconciliation[];
  anomalies: AnomalyItem[];
  explanation: string;
}

/* ---- Filter tabs ---- */

type FilterTab = "tous" | "solde" | "solde_non_rapproche" | "partiellement_paye" | "en_attente" | "incoherent";

const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: "tous", label: "Tous" },
  { key: "solde", label: "Soldes" },
  { key: "solde_non_rapproche", label: "Non rapproches" },
  { key: "partiellement_paye", label: "Partiellement payes" },
  { key: "en_attente", label: "En attente" },
  { key: "incoherent", label: "Incoherents" },
];

const CONFIDENCE_COLORS: Record<string, string> = {
  certain: "bg-emerald-100 text-emerald-700",
  probable: "bg-blue-100 text-blue-700",
  partiel: "bg-amber-100 text-amber-700",
  incertain: "bg-red-100 text-red-700",
};

/* ---- Component ---- */

export default function RapprochementCosiumPage() {
  const [activeTab, setActiveTab] = useState<FilterTab>("tous");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [linking, setLinking] = useState(false);

  // Build query params
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

  // Detail data for expanded row
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

  // KPI values
  const totalDossiers = summary?.total_customers ?? 0;
  const soldes = summary?.solde ?? 0;
  const nonRapproches = summary?.solde_non_rapproche ?? 0;
  const partiels = summary?.partiellement_paye ?? 0;
  const incoherents = summary?.incoherent ?? 0;
  const totalFacture = summary?.total_facture ?? 0;
  const totalImpaye = summary?.total_outstanding ?? 0;
  const tauxSolde = totalDossiers > 0 ? Math.round(((soldes + nonRapproches) / totalDossiers) * 100) : 0;

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
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <KPICard
          icon={Users}
          label="Total dossiers"
          value={totalDossiers.toLocaleString("fr-FR")}
          color="primary"
        />
        <KPICard
          icon={CheckCircle}
          label={`Soldes (${tauxSolde}%)`}
          value={soldes.toLocaleString("fr-FR")}
          color="success"
        />
        <KPICard
          icon={ArrowLeftRight}
          label="Non rapproches"
          value={nonRapproches.toLocaleString("fr-FR")}
          color="primary"
        />
        <KPICard
          icon={AlertCircle}
          label="Partiellement payes"
          value={partiels.toLocaleString("fr-FR")}
          color="warning"
        />
        <KPICard
          icon={AlertCircle}
          label="Incoherents"
          value={incoherents.toLocaleString("fr-FR")}
          color="danger"
        />
        <KPICard
          icon={Euro}
          label="Total impaye"
          value={formatMoney(totalImpaye)}
          color={totalImpaye > 0 ? "danger" : "success"}
        />
      </div>

      {/* Summary amounts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Total facture</p>
            <p className="text-lg font-bold tabular-nums text-text-primary">{formatMoney(totalFacture)}</p>
          </div>
          <FileText className="h-8 w-8 text-gray-200" aria-hidden="true" />
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-text-secondary">Total impaye</p>
            <p className="text-lg font-bold tabular-nums text-red-700">{formatMoney(totalImpaye)}</p>
          </div>
          <Euro className="h-8 w-8 text-red-200" aria-hidden="true" />
        </div>
      </div>

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

/* ---- Row component ---- */

function ReconciliationRow({
  item,
  isExpanded,
  onToggle,
  detail,
  detailLoading,
}: {
  item: ReconciliationListItem;
  isExpanded: boolean;
  onToggle: () => void;
  detail: CustomerReconciliation | null;
  detailLoading: boolean;
}) {
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

      {/* Expanded detail */}
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

/* ---- Expanded detail ---- */

function ExpandedDetail({ detail }: { detail: CustomerReconciliation }) {
  return (
    <div className="space-y-4">
      {/* Explanation */}
      <div className="rounded-lg border border-border bg-white p-3">
        <p className="text-sm text-text-primary">{detail.explanation}</p>
      </div>

      {/* Anomalies */}
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

      {/* Per-invoice breakdown */}
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
