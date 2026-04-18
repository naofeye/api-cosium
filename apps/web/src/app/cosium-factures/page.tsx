"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { Button } from "@/components/ui/Button";
import { useCosiumInvoices, useCosiumInvoiceTotals } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { formatMoney, formatDate } from "@/lib/format";
import { Download, Receipt, Euro, AlertCircle, FileText } from "lucide-react";
import type { CosiumInvoice } from "@/lib/types";

const TYPE_OPTIONS = [
  { value: "INVOICE", label: "Factures uniquement" },
  { value: "", label: "Tous les types" },
  { value: "QUOTE", label: "Devis" },
  { value: "CREDIT_NOTE", label: "Avoir" },
];

const SETTLED_OPTIONS = [
  { value: "", label: "Tous les statuts" },
  { value: "true", label: "Solde" },
  { value: "false", label: "Impaye" },
];

function typeLabel(type: string): string {
  switch (type) {
    case "INVOICE":
      return "Facture";
    case "QUOTE":
      return "Devis";
    case "CREDIT_NOTE":
      return "Avoir";
    default:
      return type;
  }
}

export default function CosiumFacturesPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("INVOICE");
  const [settledFilter, setSettledFilter] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [hasOutstandingFilter, setHasOutstandingFilter] = useState("");
  const [minAmount, setMinAmount] = useState("");
  const [maxAmount, setMaxAmount] = useState("");

  const settled = settledFilter === "" ? null : settledFilter === "true";
  const hasOutstanding = hasOutstandingFilter === "" ? null : hasOutstandingFilter === "true";

  const filterParams = {
    type_filter: typeFilter || undefined,
    settled: settled ?? undefined,
    search: search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    has_outstanding: hasOutstanding ?? undefined,
    min_amount: (() => {
      const n = Number(minAmount);
      return minAmount && !Number.isNaN(n) ? n : undefined;
    })(),
    max_amount: (() => {
      const n = Number(maxAmount);
      return maxAmount && !Number.isNaN(n) ? n : undefined;
    })(),
  };

  const { data, error, isLoading, mutate } = useCosiumInvoices({
    page,
    page_size: 25,
    ...filterParams,
  });

  const { data: totals } = useCosiumInvoiceTotals(filterParams);

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const handleExportCsv = () => {
    if (!data?.items?.length) return;
    const headers = ["Numero", "Date", "Client", "Type", "Montant TTC", "Solde restant", "Statut"];
    const rows = data.items.map((inv) => [
      inv.invoice_number,
      formatDate(inv.invoice_date),
      inv.customer_name || "-",
      typeLabel(inv.type),
      formatMoney(inv.total_ti),
      formatMoney(inv.outstanding_balance),
      inv.settled ? "Solde" : "Impaye",
    ]);
    exportToCsv("cosium-factures.csv", headers, rows);
  };

  const handleClientClick = (inv: CosiumInvoice) => {
    if (inv.customer_id) {
      router.push(`/clients/${inv.customer_id}`);
    }
  };

  const columns: Column<CosiumInvoice>[] = [
    {
      key: "invoice_number",
      header: "Numero",
      sortable: true,
      render: (row) => <span className="font-mono font-medium">{row.invoice_number}</span>,
    },
    {
      key: "invoice_date",
      header: "Date",
      sortable: true,
      render: (row) =>
        row.invoice_date ? <DateDisplay date={row.invoice_date} /> : <span className="text-text-secondary">-</span>,
    },
    {
      key: "customer_name",
      header: "Client",
      sortable: true,
      render: (row) => (
        row.customer_id ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleClientClick(row);
            }}
            className="text-blue-600 hover:text-blue-700 hover:underline font-medium text-left"
            title="Voir la fiche client"
          >
            {row.customer_name || "-"}
          </button>
        ) : (
          <span>{row.customer_name || "-"}</span>
        )
      ),
    },
    {
      key: "type",
      header: "Type",
      render: (row) => (
        <StatusBadge
          status={row.type === "INVOICE" ? "facturee" : row.type === "QUOTE" ? "brouillon" : "annulee"}
          label={typeLabel(row.type)}
        />
      ),
    },
    {
      key: "total_ti",
      header: "Montant TTC",
      sortable: true,
      className: "text-right",
      render: (row) => <MoneyDisplay amount={row.total_ti} bold />,
    },
    {
      key: "outstanding_balance",
      header: "Solde restant",
      sortable: true,
      className: "text-right",
      render: (row) => (
        <MoneyDisplay
          amount={row.outstanding_balance}
          className={row.outstanding_balance > 0 ? "text-red-600" : "text-emerald-600"}
        />
      ),
    },
    {
      key: "settled",
      header: "Statut",
      render: (row) =>
        row.settled ? <StatusBadge status="payee" label="Solde" /> : <StatusBadge status="impayee" label="Impaye" />,
    },
  ];

  return (
    <PageLayout
      title="Factures Cosium"
      description={`${data?.total ?? 0} documents synchronises depuis Cosium`}
      breadcrumb={[{ label: "Factures Cosium" }]}
      actions={
        <Button variant="outline" onClick={handleExportCsv} disabled={!data?.items?.length}>
          <Download className="h-4 w-4 mr-1" /> Exporter CSV
        </Button>
      }
    >
      {/* KPI bar with server-side totals */}
      {totals && totals.count > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-blue-50 p-2">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Nombre de documents</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums">{totals.count}</p>
            </div>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-emerald-50 p-2">
              <Euro className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total TTC</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums">{formatMoney(totals.total_ttc)}</p>
            </div>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-red-50 p-2">
              <AlertCircle className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total impaye</p>
              <p className="text-xl font-bold text-red-600 tabular-nums">{formatMoney(totals.total_impaye)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher par numero ou client..." onSearch={handleSearch} />
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label="Filtrer par type"
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          value={settledFilter}
          onChange={(e) => {
            setSettledFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label="Filtrer par statut"
        >
          {SETTLED_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-2">
          <label className="text-sm text-text-secondary" htmlFor="date-from">Du</label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <label className="text-sm text-text-secondary" htmlFor="date-to">au</label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          value={hasOutstandingFilter}
          onChange={(e) => { setHasOutstandingFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label="Filtrer par encours"
        >
          <option value="">Tous (encours)</option>
          <option value="true">Avec encours &gt; 0</option>
          <option value="false">Sans encours</option>
        </select>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="Min EUR"
            value={minAmount}
            onChange={(e) => { setMinAmount(e.target.value); setPage(1); }}
            className="w-24 rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Montant minimum"
          />
          <input
            type="number"
            placeholder="Max EUR"
            value={maxAmount}
            onChange={(e) => { setMaxAmount(e.target.value); setPage(1); }}
            className="w-24 rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Montant maximum"
          />
          {(dateFrom || dateTo) && (
            <button
              onClick={() => { setDateFrom(""); setDateTo(""); setPage(1); }}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              Effacer dates
            </button>
          )}
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        page={page}
        pageSize={25}
        total={data?.total}
        onPageChange={setPage}
        emptyTitle="Aucune facture Cosium"
        emptyDescription="Lancez une synchronisation depuis Parametres > Connexion ERP pour importer vos factures."
        emptyIcon={Receipt}
      />
    </PageLayout>
  );
}
