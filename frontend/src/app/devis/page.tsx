"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { useDevisList } from "@/lib/hooks/use-api";
import Link from "next/link";
import { FileText } from "lucide-react";
import type { Devis } from "@/lib/types";

export default function DevisListPage() {
  const router = useRouter();
  const { data: devisList, error, isLoading, mutate } = useDevisList();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!devisList) return [];
    if (!search.trim()) return devisList;
    const q = search.toLowerCase();
    return devisList.filter((d) => d.numero.toLowerCase().includes(q) || d.status.toLowerCase().includes(q));
  }, [search, devisList]);

  const columns: Column<Devis>[] = [
    { key: "numero", header: "Numero", render: (row) => <span className="font-mono font-medium">{row.numero}</span> },
    { key: "customer", header: "Dossier", render: (row) => `Dossier #${row.case_id}` },
    { key: "status", header: "Statut", render: (row) => <StatusBadge status={row.status} /> },
    { key: "montant_ttc", header: "Montant TTC", render: (row) => <MoneyDisplay amount={row.montant_ttc} bold /> },
    {
      key: "reste",
      header: "Reste a charge",
      render: (row) => <MoneyDisplay amount={row.reste_a_charge} colored />,
    },
    { key: "date", header: "Date", render: (row) => <DateDisplay date={row.created_at} /> },
  ];

  return (
    <PageLayout
      title="Devis"
      description="Gestion des devis clients"
      breadcrumb={[{ label: "Devis" }]}
      actions={
        <Link href="/devis/new">
          <Button>Nouveau devis</Button>
        </Link>
      }
    >
      <div className="mb-6">
        <SearchInput placeholder="Rechercher un devis..." onSearch={setSearch} />
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/devis/${row.id}`)}
        emptyTitle="Aucun devis"
        emptyDescription="Creez votre premier devis pour un client."
        emptyIcon={FileText}
        emptyAction={
          <Link href="/devis/new">
            <Button>Creer un devis</Button>
          </Link>
        }
      />
    </PageLayout>
  );
}
