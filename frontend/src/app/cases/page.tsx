"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { useCases } from "@/lib/hooks/use-api";
import Link from "next/link";
import { AlertCircle, CheckCircle } from "lucide-react";
import type { Case } from "@/lib/types";

export default function CasesPage() {
  const router = useRouter();
  const { data: cases, error, isLoading, mutate } = useCases();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!cases) return [];
    if (!search.trim()) return cases;
    const q = search.toLowerCase();
    return cases.filter(
      (c) =>
        c.customer_name.toLowerCase().includes(q) ||
        c.status.toLowerCase().includes(q) ||
        (c.source ?? "").toLowerCase().includes(q) ||
        String(c.id).includes(q),
    );
  }, [search, cases]);

  const columns: Column<Case>[] = [
    { key: "id", header: "ID", render: (row) => <span className="font-mono text-text-secondary">#{row.id}</span> },
    { key: "customer", header: "Client", render: (row) => <span className="font-medium">{row.customer_name}</span> },
    { key: "status", header: "Statut", render: (row) => <StatusBadge status={row.status} /> },
    {
      key: "docs",
      header: "Pieces",
      render: (row) => {
        if (row.missing_docs === null || row.missing_docs === undefined) return "—";
        if (row.missing_docs === 0) {
          return (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
              <CheckCircle className="h-3.5 w-3.5" />
              Complet
            </span>
          );
        }
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
            <AlertCircle className="h-3.5 w-3.5" />
            {row.missing_docs} manquante{row.missing_docs > 1 ? "s" : ""}
          </span>
        );
      },
    },
    { key: "source", header: "Source", render: (row) => row.source || "—" },
    { key: "date", header: "Date", render: (row) => <DateDisplay date={row.created_at} /> },
  ];

  return (
    <PageLayout
      title="Dossiers clients"
      description="Gestion des dossiers clients"
      breadcrumb={[{ label: "Dossiers" }]}
      actions={
        <Link href="/cases/new">
          <Button>Nouveau dossier</Button>
        </Link>
      }
    >
      <div className="mb-6">
        <SearchInput placeholder="Rechercher un dossier..." onSearch={setSearch} />
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/cases/${row.id}`)}
        emptyTitle="Aucun dossier"
        emptyDescription="Commencez par creer votre premier dossier client."
        emptyAction={
          <Link href="/cases/new">
            <Button>Creer un dossier</Button>
          </Link>
        }
      />
    </PageLayout>
  );
}
