"use client";

import { useState, useCallback } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { useCosiumDoctors } from "@/lib/hooks/use-api";
import { Stethoscope } from "lucide-react";
import type { CosiumDoctor } from "@/lib/types";

export default function PrescripteursPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const { data, error, isLoading, mutate } = useCosiumDoctors({
    page,
    page_size: 50,
    search: search || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const columns: Column<CosiumDoctor>[] = [
    {
      key: "lastname",
      header: "Nom",
      sortable: true,
      render: (row) => (
        <span className="font-medium">
          {row.civility ? `${row.civility} ` : ""}
          {row.lastname}
        </span>
      ),
    },
    {
      key: "firstname",
      header: "Prenom",
      sortable: true,
      render: (row) => row.firstname || <span className="text-text-secondary">-</span>,
    },
    {
      key: "specialty",
      header: "Specialite",
      render: (row) => row.specialty || <span className="text-text-secondary">-</span>,
    },
    {
      key: "rpps_number",
      header: "RPPS",
      render: (row) => (
        <span className="font-mono text-sm">{row.rpps_number || "-"}</span>
      ),
    },
    {
      key: "email",
      header: "Email",
      render: (row) =>
        row.email ? (
          <a href={`mailto:${row.email}`} className="text-primary hover:underline text-sm">
            {row.email}
          </a>
        ) : (
          <span className="text-text-secondary">-</span>
        ),
    },
    {
      key: "phone",
      header: "Telephone",
      render: (row) => row.phone || <span className="text-text-secondary">-</span>,
    },
    {
      key: "optic_prescriber",
      header: "Prescripteur",
      render: (row) => (
        <div className="flex gap-1">
          {row.optic_prescriber && <StatusBadge status="acceptee" label="Optique" />}
          {row.audio_prescriber && <StatusBadge status="en_cours" label="Audio" />}
          {!row.optic_prescriber && !row.audio_prescriber && (
            <StatusBadge status="brouillon" label="Aucun" />
          )}
        </div>
      ),
    },
  ];

  return (
    <ErrorBoundary name="Prescripteurs">
    <PageLayout
      title="Prescripteurs Cosium"
      description={`${data?.total ?? 0} prescripteurs synchronises`}
      breadcrumb={[{ label: "Prescripteurs" }]}
    >
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher un prescripteur..." onSearch={handleSearch} />
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        page={page}
        pageSize={50}
        total={data?.total}
        onPageChange={setPage}
        emptyTitle="Aucun prescripteur"
        emptyDescription="Les medecins prescripteurs sont importes depuis Cosium. Lancez une synchronisation."
        emptyIcon={Stethoscope}
      />
    </PageLayout>
    </ErrorBoundary>
  );
}
