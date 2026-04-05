"use client";

import { useState, useCallback, useMemo } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { Button } from "@/components/ui/Button";
import { useCosiumInvoices } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { formatMoney, formatDate } from "@/lib/format";
import { Download, Receipt } from "lucide-react";
import type { CosiumInvoice } from "@/lib/types";

const TYPE_OPTIONS = [
  { value: "", label: "Tous les types" },
  { value: "INVOICE", label: "Facture" },
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
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("");
  const [settledFilter, setSettledFilter] = useState("");
  const [search, setSearch] = useState("");

  const settled = settledFilter === "" ? null : settledFilter === "true";

  const { data, error, isLoading, mutate } = useCosiumInvoices({
    page,
    page_size: 25,
    type_filter: typeFilter || undefined,
    settled: settled ?? undefined,
    search: search || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const stats = useMemo(() => {
    const items = data?.items ?? [];
    if (items.length === 0) return null;
    const totalTTC = items.reduce((sum, inv) => sum + inv.total_ti, 0);
    const totalImpaye = items.reduce((sum, inv) => sum + inv.outstanding_balance, 0);
    const invoiceCount = items.filter((inv) => inv.type === "INVOICE").length;
    const quoteCount = items.filter((inv) => inv.type === "QUOTE").length;
    const creditCount = items.filter((inv) => inv.type === "CREDIT_NOTE").length;
    return { totalTTC, totalImpaye, invoiceCount, quoteCount, creditCount };
  }, [data]);

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
      render: (row) => row.customer_name || "-",
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
      {stats && (
        <div className="flex items-center gap-6 mb-4 text-sm text-text-secondary">
          <span>Total TTC : <span className="font-semibold text-text-primary">{formatMoney(stats.totalTTC)}</span></span>
          <span className="text-gray-300">|</span>
          <span>Impaye : <span className="font-semibold text-red-600">{formatMoney(stats.totalImpaye)}</span></span>
          <span className="text-gray-300">|</span>
          <span>{stats.invoiceCount} facture{stats.invoiceCount > 1 ? "s" : ""}</span>
          <span className="text-gray-300">|</span>
          <span>{stats.quoteCount} devis</span>
          {stats.creditCount > 0 && (
            <>
              <span className="text-gray-300">|</span>
              <span>{stats.creditCount} avoir{stats.creditCount > 1 ? "s" : ""}</span>
            </>
          )}
        </div>
      )}

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
