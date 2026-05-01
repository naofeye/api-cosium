"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { KPICard } from "@/components/ui/KPICard";
import { Shield, CheckCircle, Clock, XCircle } from "lucide-react";
import type { PecRequest } from "@/lib/types";

export default function PecPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const params = statusFilter ? `?status=${statusFilter}` : "";
  const { data: pecs, error, isLoading, mutate } = useSWR<PecRequest[]>(`/pec${params}`);

  const filtered = useMemo(() => {
    if (!pecs) return [];
    if (!search.trim()) return pecs;
    const q = search.toLowerCase();
    return pecs.filter(
      (p) =>
        (p.organization_name || "").toLowerCase().includes(q) ||
        (p.customer_name || "").toLowerCase().includes(q) ||
        p.status.toLowerCase().includes(q),
    );
  }, [search, pecs]);

  const counts = {
    soumise: (pecs ?? []).filter((p) => p.status === "soumise").length,
    en_attente: (pecs ?? []).filter((p) => p.status === "en_attente").length,
    acceptee: (pecs ?? []).filter((p) => p.status === "acceptee").length,
    refusee: (pecs ?? []).filter((p) => p.status === "refusee").length,
  };

  const columns: Column<PecRequest>[] = [
    { key: "id", header: "ID", render: (row) => <span className="font-mono text-text-secondary">#{row.id}</span> },
    {
      key: "customer",
      header: "Client",
      render: (row) => <span className="font-medium">{row.customer_name || "-"}</span>,
    },
    { key: "org", header: "Organisme", render: (row) => row.organization_name || "-" },
    { key: "status", header: "Statut", render: (row) => <StatusBadge status={row.status} /> },
    { key: "demande", header: "Demande", render: (row) => <MoneyDisplay amount={row.montant_demande} /> },
    {
      key: "accorde",
      header: "Accorde",
      render: (row) =>
        row.montant_accorde !== null ? (
          <MoneyDisplay amount={row.montant_accorde} colored />
        ) : (
          <span className="text-text-secondary">-</span>
        ),
    },
    { key: "date", header: "Date", render: (row) => <DateDisplay date={row.created_at} /> },
  ];

  return (
    <PageLayout
      title="PEC / Tiers payant"
      description="Suivi des prises en charge mutuelles et securite sociale"
      breadcrumb={[{ label: "PEC" }]}
    >
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KPICard icon={Shield} label="Soumises" value={counts.soumise} color="info" />
        <KPICard icon={Clock} label="En attente" value={counts.en_attente} color="warning" />
        <KPICard icon={CheckCircle} label="Acceptees" value={counts.acceptee} color="success" />
        <KPICard icon={XCircle} label="Refusees" value={counts.refusee} color="danger" />
      </div>

      <div className="flex items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher..." onSearch={setSearch} />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filtrer par statut"
          className="rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">Tous les statuts</option>
          <option value="soumise">Soumise</option>
          <option value="en_attente">En attente</option>
          <option value="acceptee">Acceptee</option>
          <option value="refusee">Refusee</option>
          <option value="partielle">Partielle</option>
          <option value="cloturee">Cloturee</option>
        </select>
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/pec/${row.id}`)}
        getRowHref={(row) => `/pec/${row.id}`}
        emptyTitle="Aucune demande de PEC"
        emptyDescription="Aucune demande de prise en charge. Creez une PEC depuis un dossier client."
        emptyIcon={Shield}
      />
    </PageLayout>
  );
}
