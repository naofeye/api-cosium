"use client";

import { useState, useCallback } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { SearchInput } from "@/components/ui/SearchInput";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { useCosiumPrescriptions } from "@/lib/hooks/use-api";
import { ClipboardList } from "lucide-react";
import type { CosiumPrescription } from "@/lib/types";

function formatDiopter(value: number | null): string {
  if (value === null || value === undefined) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function formatAxis(value: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value}°`;
}

export default function OrdonnancesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const { data, error, isLoading, mutate } = useCosiumPrescriptions({
    page,
    page_size: 25,
    search: search || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const columns: Column<CosiumPrescription>[] = [
    {
      key: "prescription_date",
      header: "Date",
      sortable: true,
      render: (row) =>
        row.prescription_date ? (
          <DateDisplay date={row.prescription_date} />
        ) : (
          <span className="text-text-secondary">-</span>
        ),
    },
    {
      key: "prescriber_name",
      header: "Prescripteur",
      sortable: true,
      render: (row) => row.prescriber_name || <span className="text-text-secondary">-</span>,
    },
    {
      key: "od_sphere",
      header: "OD Sphere",
      className: "text-right font-mono",
      render: (row) => formatDiopter(row.sphere_right),
    },
    {
      key: "od_cylinder",
      header: "OD Cylindre",
      className: "text-right font-mono",
      render: (row) => formatDiopter(row.cylinder_right),
    },
    {
      key: "od_axis",
      header: "OD Axe",
      className: "text-right font-mono",
      render: (row) => formatAxis(row.axis_right),
    },
    {
      key: "od_addition",
      header: "OD Add.",
      className: "text-right font-mono",
      render: (row) => formatDiopter(row.addition_right),
    },
    {
      key: "og_sphere",
      header: "OG Sphere",
      className: "text-right font-mono",
      render: (row) => formatDiopter(row.sphere_left),
    },
    {
      key: "og_cylinder",
      header: "OG Cylindre",
      className: "text-right font-mono",
      render: (row) => formatDiopter(row.cylinder_left),
    },
    {
      key: "og_axis",
      header: "OG Axe",
      className: "text-right font-mono",
      render: (row) => formatAxis(row.axis_left),
    },
    {
      key: "og_addition",
      header: "OG Add.",
      className: "text-right font-mono",
      render: (row) => formatDiopter(row.addition_left),
    },
  ];

  return (
    <PageLayout
      title="Ordonnances Cosium"
      description={`${data?.total ?? 0} ordonnances synchronisees`}
      breadcrumb={[{ label: "Ordonnances" }]}
    >
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher par prescripteur..." onSearch={handleSearch} />
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
        emptyTitle="Aucune ordonnance"
        emptyDescription="Les ordonnances sont importees depuis Cosium. Lancez une synchronisation."
        emptyIcon={ClipboardList}
      />
    </PageLayout>
  );
}
