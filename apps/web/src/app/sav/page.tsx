"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Briefcase } from "lucide-react";

interface SAVItem {
  cosium_id: number | null;
  status: string | null;
  resolution_status: string | null;
  creation_date: string | null;
  processing_date: string | null;
  end_date: string | null;
  description: string | null;
  type: string | null;
  customer_number: string | null;
  invoice_number: string | null;
  product_model: string | null;
  product_color: string | null;
  repairer_name: string | null;
  site_name: string | null;
}

const STATUS_OPTIONS = [
  { value: "", label: "Tous statuts" },
  { value: "TO_REPAIR", label: "A reparer" },
  { value: "IN_PROCESS", label: "En cours" },
  { value: "REPAIR_IN_PROCESS", label: "Reparation en cours" },
  { value: "FINISHED", label: "Termine" },
];

function statusToBadge(status: string | null): { label: string; statusKey: string } {
  switch (status) {
    case "TO_REPAIR": return { label: "A reparer", statusKey: "en_attente" };
    case "IN_PROCESS": return { label: "En cours", statusKey: "en_cours" };
    case "REPAIR_IN_PROCESS": return { label: "Reparation en cours", statusKey: "en_cours" };
    case "FINISHED": return { label: "Termine", statusKey: "termine" };
    default: return { label: status ?? "?", statusKey: "brouillon" };
  }
}

function frenchDate(iso: string | null): string {
  if (!iso) return "-";
  try { return new Date(iso).toLocaleDateString("fr-FR"); } catch { return iso.slice(0, 10); }
}

export default function SAVPage() {
  const [status, setStatus] = useState<string>("");
  const queryString = status ? `?status=${status}&page_size=100` : "?page_size=100";
  const { data: rawData, error, isLoading, mutate } = useSWR<SAVItem[]>(`/cosium/sav${queryString}`);
  const data = (rawData ?? []).map((r, idx) => ({ ...r, id: r.cosium_id ?? -idx - 1 }));
  type SAVRow = SAVItem & { id: number };

  const columns: Column<SAVRow>[] = [
    {
      key: "cosium_id",
      header: "N°",
      render: (r) => <span className="font-mono text-xs">{r.cosium_id ?? "-"}</span>,
    },
    {
      key: "status",
      header: "Statut",
      render: (r) => {
        const b = statusToBadge(r.status);
        return <StatusBadge status={b.statusKey} label={b.label} />;
      },
    },
    {
      key: "creation_date",
      header: "Cree le",
      render: (r) => frenchDate(r.creation_date),
    },
    {
      key: "customer_number",
      header: "Client",
      render: (r) => r.customer_number ?? "-",
    },
    {
      key: "product_model",
      header: "Produit",
      render: (r) => (
        <div className="text-sm">
          <p className="font-medium">{r.product_model ?? "-"}</p>
          {r.product_color && <p className="text-xs text-text-secondary">{r.product_color}</p>}
        </div>
      ),
    },
    {
      key: "description",
      header: "Description",
      render: (r) => <span className="text-sm text-text-secondary">{r.description ?? "-"}</span>,
    },
    {
      key: "repairer_name",
      header: "Reparateur",
      render: (r) => r.repairer_name ?? "-",
    },
    {
      key: "site_name",
      header: "Site",
      render: (r) => r.site_name ?? "-",
    },
  ];

  return (
    <PageLayout
      title="SAV - Apres-vente"
      description="Suivi des dossiers de reparation et garanties Cosium (lecture seule)"
      breadcrumb={[{ label: "Cosium" }, { label: "SAV" }]}
    >
      <div className="mb-6 flex items-center gap-3">
        <label className="text-sm font-medium text-text-secondary">Statut :</label>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {isLoading && <LoadingState text="Chargement des dossiers SAV..." />}
      {error && <ErrorState message="Impossible de charger les dossiers SAV" onRetry={() => mutate()} />}
      {!isLoading && !error && data.length === 0 && (
        <EmptyState
          title="Aucun dossier SAV"
          description={status ? "Aucun dossier dans ce statut. Modifiez le filtre pour voir d'autres dossiers." : "Aucun dossier de reparation actif dans Cosium."}
        />
      )}
      {!isLoading && !error && data.length > 0 && (
        <DataTable columns={columns} data={data} />
      )}
    </PageLayout>
  );
}
