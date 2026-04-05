"use client";

import { useState, useCallback, useMemo } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { KPICard } from "@/components/ui/KPICard";
import { useCosiumPayments } from "@/lib/hooks/use-api";
import { formatMoney } from "@/lib/format";
import { Euro, TrendingUp, TrendingDown } from "lucide-react";
import type { CosiumPaymentItem } from "@/lib/types";

function paymentTypeLabel(type: string): string {
  switch (type?.toUpperCase()) {
    case "CHQ": return "Cheque";
    case "CB": return "Carte bancaire";
    case "ESP": return "Especes";
    case "VIR": return "Virement";
    case "PRLV": return "Prelevement";
    default: return type || "-";
  }
}

export default function CosiumPaiementsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data, error, isLoading, mutate } = useCosiumPayments({
    page,
    page_size: 25,
    search: search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const totals = useMemo(() => {
    if (!data?.items?.length) return { positive: 0, negative: 0, net: 0 };
    let positive = 0;
    let negative = 0;
    for (const item of data.items) {
      if (item.amount >= 0) positive += item.amount;
      else negative += item.amount;
    }
    return { positive, negative, net: positive + negative };
  }, [data]);

  const columns: Column<CosiumPaymentItem>[] = [
    {
      key: "due_date",
      header: "Date",
      sortable: true,
      render: (row) =>
        row.due_date ? <DateDisplay date={row.due_date} /> : <span className="text-text-secondary">-</span>,
    },
    {
      key: "issuer_name",
      header: "Client",
      sortable: true,
      render: (row) => row.issuer_name || <span className="text-text-secondary">-</span>,
    },
    {
      key: "amount",
      header: "Montant",
      sortable: true,
      className: "text-right",
      render: (row) => (
        <MoneyDisplay
          amount={row.amount}
          bold
          className={row.amount >= 0 ? "text-emerald-600" : "text-red-600"}
        />
      ),
    },
    {
      key: "type",
      header: "Type",
      render: (row) => (
        <StatusBadge
          status={row.type === "CB" ? "en_cours" : row.type === "ESP" ? "acceptee" : "brouillon"}
          label={paymentTypeLabel(row.type)}
        />
      ),
    },
    {
      key: "bank",
      header: "Banque",
      render: (row) => row.bank || <span className="text-text-secondary">-</span>,
    },
    {
      key: "payment_number",
      header: "Reference",
      render: (row) => (
        <span className="font-mono text-sm">{row.payment_number || "-"}</span>
      ),
    },
    {
      key: "site_name",
      header: "Site",
      render: (row) => row.site_name || "-",
    },
  ];

  return (
    <PageLayout
      title="Paiements Cosium"
      description={`${data?.total ?? 0} paiements synchronises`}
      breadcrumb={[{ label: "Paiements Cosium" }]}
    >
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <KPICard icon={TrendingUp} label="Encaissements" value={formatMoney(totals.positive)} color="success" />
        <KPICard icon={TrendingDown} label="Remboursements" value={formatMoney(totals.negative)} color="danger" />
        <KPICard icon={Euro} label="Solde net (page)" value={formatMoney(totals.net)} color="primary" />
      </div>

      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher par client ou reference..." onSearch={handleSearch} />
        <div className="flex items-center gap-2">
          <label htmlFor="pay-date-from" className="text-sm text-text-secondary">Du</label>
          <input
            id="pay-date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="pay-date-to" className="text-sm text-text-secondary">Au</label>
          <input
            id="pay-date-to"
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
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
        emptyTitle="Aucun paiement"
        emptyDescription="Aucun paiement trouve dans Cosium pour les criteres selectionnes."
      />
    </PageLayout>
  );
}
