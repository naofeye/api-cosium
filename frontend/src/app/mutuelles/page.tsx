"use client";

import { useState, useCallback } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { useCosiumMutuelles } from "@/lib/hooks/use-api";
import type { CosiumMutuelle } from "@/lib/types";

export default function MutuellesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const { data, error, isLoading, mutate } = useCosiumMutuelles({
    page,
    page_size: 50,
    search: search || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const columns: Column<CosiumMutuelle>[] = [
    {
      key: "name",
      header: "Nom",
      sortable: true,
      render: (row) => <span className="font-medium">{row.name}</span>,
    },
    {
      key: "code",
      header: "Code",
      render: (row) => <span className="font-mono text-sm">{row.code || "-"}</span>,
    },
    {
      key: "phone",
      header: "Telephone",
      render: (row) => row.phone || <span className="text-text-secondary">-</span>,
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
      key: "city",
      header: "Ville",
      sortable: true,
      render: (row) => row.city || <span className="text-text-secondary">-</span>,
    },
    {
      key: "opto_amc",
      header: "Opto AMC",
      render: (row) =>
        row.opto_amc ? (
          <StatusBadge status="acceptee" label="Oui" />
        ) : (
          <StatusBadge status="brouillon" label="Non" />
        ),
    },
    {
      key: "hidden",
      header: "Statut",
      render: (row) =>
        row.hidden ? (
          <StatusBadge status="archive" label="Masquee" />
        ) : (
          <StatusBadge status="complet" label="Active" />
        ),
    },
  ];

  return (
    <PageLayout
      title="Mutuelles Cosium"
      description={`${data?.total ?? 0} organismes complementaires`}
      breadcrumb={[{ label: "Mutuelles" }]}
    >
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher une mutuelle..." onSearch={handleSearch} />
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
        emptyTitle="Aucune mutuelle"
        emptyDescription="Aucune mutuelle trouvee dans Cosium. Synchronisez vos donnees depuis les parametres."
      />
    </PageLayout>
  );
}
