"use client";

import { useState, useCallback } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { SearchInput } from "@/components/ui/SearchInput";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { Button } from "@/components/ui/Button";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useCosiumProducts } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { formatMoney } from "@/lib/format";
import { Download, Package, Tag } from "lucide-react";
import type { CosiumProduct } from "@/lib/types";

export default function ProduitsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [familyFilter, setFamilyFilter] = useState("");

  const { data, error, isLoading, mutate } = useCosiumProducts({
    page,
    page_size: 25,
    search: search || undefined,
    family: familyFilter || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const handleExportCsv = () => {
    if (!data?.items?.length) return;
    const headers = ["Code", "EAN", "Libelle", "Famille", "Prix TTC"];
    const rows = data.items.map((p) => [
      p.code,
      p.ean_code,
      p.label,
      p.family_type,
      formatMoney(p.price),
    ]);
    exportToCsv("produits-cosium.csv", headers, rows);
  };

  // Extract unique families for filter dropdown
  const families = data?.items
    ? [...new Set(data.items.map((p) => p.family_type).filter(Boolean))].sort()
    : [];

  const columns: Column<CosiumProduct>[] = [
    {
      key: "code",
      header: "Code",
      sortable: true,
      render: (row) => (
        <span className="font-mono font-medium text-sm">{row.code || "-"}</span>
      ),
    },
    {
      key: "ean_code",
      header: "EAN",
      sortable: true,
      render: (row) => (
        <span className="font-mono text-sm text-gray-600">{row.ean_code || "-"}</span>
      ),
    },
    {
      key: "label",
      header: "Libelle",
      sortable: true,
      render: (row) => (
        <span className="text-sm font-medium text-gray-900 truncate max-w-xs block" title={row.label}>
          {row.label || "-"}
        </span>
      ),
    },
    {
      key: "family_type",
      header: "Famille",
      sortable: true,
      render: (row) =>
        row.family_type ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
            <Tag className="h-3 w-3" aria-hidden="true" />
            {row.family_type}
          </span>
        ) : (
          <span className="text-gray-400 text-sm">-</span>
        ),
    },
    {
      key: "price",
      header: "Prix TTC",
      sortable: true,
      className: "text-right",
      render: (row) => <MoneyDisplay amount={row.price} bold />,
    },
  ];

  return (
    <ErrorBoundary name="Produits Cosium">
      <PageLayout
        title="Produits Cosium"
        description={`${data?.total ?? 0} produits synchronises depuis Cosium`}
        breadcrumb={[{ label: "Produits Cosium" }]}
        actions={
          <Button variant="outline" onClick={handleExportCsv} disabled={!data?.items?.length}>
            <Download className="h-4 w-4 mr-1" /> Exporter CSV
          </Button>
        }
      >
        {/* KPI bar */}
        {data && data.total > 0 && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
              <div className="rounded-lg bg-blue-50 p-2">
                <Package className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Total produits</p>
                <p className="text-xl font-bold text-gray-900 tabular-nums">{data.total}</p>
              </div>
            </div>
            <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
              <div className="rounded-lg bg-emerald-50 p-2">
                <Tag className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Familles</p>
                <p className="text-xl font-bold text-gray-900 tabular-nums">{families.length}</p>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <SearchInput placeholder="Rechercher par libelle, code ou EAN..." onSearch={handleSearch} />
          <select
            value={familyFilter}
            onChange={(e) => {
              setFamilyFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Filtrer par famille"
          >
            <option value="">Toutes les familles</option>
            {families.map((f) => (
              <option key={f} value={f}>{f}</option>
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
          emptyTitle="Aucun produit Cosium"
          emptyDescription="Lancez une synchronisation depuis Parametres > Connexion ERP pour importer vos produits."
          emptyIcon={Package}
        />
      </PageLayout>
    </ErrorBoundary>
  );
}
