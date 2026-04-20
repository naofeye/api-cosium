"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { useCosiumInvoices, useCosiumInvoiceTotals } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { formatMoney, formatDate } from "@/lib/format";
import { Download, Receipt, Euro, AlertCircle, FileText } from "lucide-react";
import type { CosiumInvoice } from "@/lib/types";
import { InvoiceFilters } from "./components/InvoiceFilters";
import { buildInvoiceColumns, typeLabel } from "./components/invoice-columns";

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

  const columns = buildInvoiceColumns(handleClientClick);

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

      <InvoiceFilters
        typeFilter={typeFilter}
        settledFilter={settledFilter}
        dateFrom={dateFrom}
        dateTo={dateTo}
        hasOutstandingFilter={hasOutstandingFilter}
        minAmount={minAmount}
        maxAmount={maxAmount}
        onSearch={handleSearch}
        onTypeChange={(v) => { setTypeFilter(v); setPage(1); }}
        onSettledChange={(v) => { setSettledFilter(v); setPage(1); }}
        onDateFromChange={(v) => { setDateFrom(v); setPage(1); }}
        onDateToChange={(v) => { setDateTo(v); setPage(1); }}
        onHasOutstandingChange={(v) => { setHasOutstandingFilter(v); setPage(1); }}
        onMinAmountChange={(v) => { setMinAmount(v); setPage(1); }}
        onMaxAmountChange={(v) => { setMaxAmount(v); setPage(1); }}
        onClearDates={() => { setDateFrom(""); setDateTo(""); setPage(1); }}
      />

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
