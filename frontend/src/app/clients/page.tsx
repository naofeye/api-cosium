"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { useClients } from "@/lib/hooks/use-api";
import Link from "next/link";
import type { Customer } from "@/lib/types";

export default function ClientsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, error, isLoading, mutate } = useClients({ q: search || undefined, page });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const columns: Column<Customer>[] = [
    { key: "id", header: "ID", render: (row) => <span className="font-mono text-text-secondary">#{row.id}</span> },
    {
      key: "name",
      header: "Nom",
      render: (row) => (
        <span className="font-medium">
          {row.last_name} {row.first_name}
        </span>
      ),
    },
    { key: "phone", header: "Telephone", render: (row) => row.phone || "—" },
    { key: "email", header: "Email", render: (row) => row.email || "—" },
    { key: "city", header: "Ville", render: (row) => row.city || "—" },
    { key: "date", header: "Cree le", render: (row) => <DateDisplay date={row.created_at} /> },
  ];

  return (
    <PageLayout
      title="Clients"
      description="Gestion des clients"
      breadcrumb={[{ label: "Clients" }]}
      actions={
        <Link href="/clients/new">
          <Button>Nouveau client</Button>
        </Link>
      }
    >
      <div className="mb-6">
        <SearchInput placeholder="Rechercher un client (nom, email, telephone, ville)..." onSearch={handleSearch} />
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/clients/${row.id}`)}
        emptyTitle="Aucun client"
        emptyDescription="Commencez par creer votre premier client."
        emptyAction={
          <Link href="/clients/new">
            <Button>Creer un client</Button>
          </Link>
        }
        page={page}
        pageSize={25}
        total={data?.total}
        onPageChange={setPage}
      />
    </PageLayout>
  );
}
