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
import { Download, RotateCcw, Euro, FileText } from "lucide-react";
import type { CosiumInvoice } from "@/lib/types";

const SETTLED_OPTIONS = [
  { value: "", label: "Tous les statuts" },
  { value: "true", label: "Solde" },
  { value: "false", label: "Non solde" },
];

export default function AvoirsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [settledFilter, setSettledFilter] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const settled = settledFilter === "" ? null : settledFilter === "true";

  const filterParams = {
    type_filter: "CREDIT_NOTE" as string,
    settled: settled ?? undefined,
    search: search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
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
    const headers = ["Numero", "Date", "Client", "Montant TTC", "Solde restant", "Statut"];
    const rows = data.items.map((inv) => [
      inv.invoice_number,
      formatDate(inv.invoice_date),
      inv.customer_name || "-",
      formatMoney(inv.total_ti),
      formatMoney(inv.outstanding_balance),
      inv.settled ? "Solde" : "Non solde",
    ]);
    exportToCsv("avoirs-cosium.csv", headers, rows);
  };

  const handleClientClick = (inv: CosiumInvoice) => {
    if (inv.customer_id) {
      router.push(`/clients/${inv.customer_id}`);
    }
  };

  const columns: Column<CosiumInvoice>[] = [
    {
      key: "invoice_number",
      header: "N\u00b0 Avoir",
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
      render: (row) =>
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
        row.settled ? <StatusBadge status="payee" label="Solde" /> : <StatusBadge status="en_attente" label="Non solde" />,
    },
  ];

  return (
    <PageLayout
      title="Avoirs Cosium"
      description={`${data?.total ?? 0} avoirs synchronises depuis Cosium`}
      breadcrumb={[{ label: "Avoirs Cosium" }]}
      actions={
        <Button variant="outline" onClick={handleExportCsv} disabled={!data?.items?.length}>
          <Download className="h-4 w-4 mr-1" /> Exporter CSV
        </Button>
      }
    >
      {/* KPI bar */}
      {totals && totals.count > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-purple-50 p-2">
              <FileText className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Nombre d&apos;avoirs</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums">{totals.count.toLocaleString("fr-FR")}</p>
            </div>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-emerald-50 p-2">
              <Euro className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total avoirs TTC</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums">{formatMoney(totals.total_ttc)}</p>
            </div>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-amber-50 p-2">
              <RotateCcw className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Solde restant</p>
              <p className="text-xl font-bold text-amber-600 tabular-nums">{formatMoney(totals.total_impaye)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher par numero ou client..." onSearch={handleSearch} />
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
          <label className="text-sm text-text-secondary" htmlFor="date-from">
            Du
          </label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <label className="text-sm text-text-secondary" htmlFor="date-to">
            au
          </label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {(dateFrom || dateTo) && (
            <button
              onClick={() => {
                setDateFrom("");
                setDateTo("");
                setPage(1);
              }}
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
        emptyTitle="Aucun avoir Cosium"
        emptyDescription="Les avoirs apparaitront ici apres synchronisation depuis Cosium."
        emptyIcon={RotateCcw}
      />
    </PageLayout>
  );
}
