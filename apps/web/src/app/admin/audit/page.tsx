"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { cn } from "@/lib/utils";
import { Shield } from "lucide-react";

interface AuditLogEntry {
  id: number;
  user_id: number;
  user_email: string | null;
  action: string;
  entity_type: string;
  entity_id: number;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

interface AuditLogList {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

const ACTION_OPTIONS = [
  { value: "", label: "Toutes les actions" },
  { value: "create", label: "Creation" },
  { value: "update", label: "Modification" },
  { value: "delete", label: "Suppression" },
  { value: "login", label: "Connexion" },
  { value: "sync", label: "Synchronisation" },
];

const ENTITY_OPTIONS = [
  { value: "", label: "Toutes les entites" },
  { value: "customer", label: "Client" },
  { value: "case", label: "Dossier" },
  { value: "devis", label: "Devis" },
  { value: "facture", label: "Facture" },
  { value: "payment", label: "Paiement" },
  { value: "document", label: "Document" },
  { value: "pec_request", label: "PEC" },
  { value: "user", label: "Utilisateur" },
  { value: "campaign", label: "Campagne" },
];

const ACTION_BADGE_COLORS: Record<string, string> = {
  create: "bg-emerald-100 text-emerald-700",
  update: "bg-blue-100 text-blue-700",
  delete: "bg-red-100 text-red-700",
  login: "bg-sky-100 text-sky-700",
  sync: "bg-amber-100 text-amber-700",
};

const ACTION_LABELS: Record<string, string> = {
  create: "Creation",
  update: "Modification",
  delete: "Suppression",
  login: "Connexion",
  sync: "Synchronisation",
};

function ActionBadge({ action }: { action: string }) {
  const colors = ACTION_BADGE_COLORS[action] ?? "bg-gray-100 text-gray-700";
  const label = ACTION_LABELS[action] ?? action;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        colors,
      )}
    >
      {label}
    </span>
  );
}

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const pageSize = 25;

  const buildUrl = useCallback(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    if (actionFilter) params.set("action", actionFilter);
    if (entityFilter) params.set("entity_type", entityFilter);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return `/audit-logs?${params.toString()}`;
  }, [page, actionFilter, entityFilter, dateFrom, dateTo]);

  const { data, error, isLoading, mutate } = useSWR<AuditLogList>(buildUrl());

  const handleFilterChange = () => {
    setPage(1);
  };

  const columns: Column<AuditLogEntry>[] = [
    {
      key: "created_at",
      header: "Date",
      sortable: true,
      render: (row) => <DateDisplay date={row.created_at} />,
    },
    {
      key: "user_email",
      header: "Utilisateur",
      render: (row) => (
        <span className="text-sm text-text-primary">
          {row.user_email ?? `#${row.user_id}`}
        </span>
      ),
    },
    {
      key: "action",
      header: "Action",
      render: (row) => <ActionBadge action={row.action} />,
    },
    {
      key: "entity_type",
      header: "Entite",
      render: (row) => (
        <span className="text-sm text-text-secondary capitalize">
          {row.entity_type.replace(/_/g, " ")}
        </span>
      ),
    },
    {
      key: "entity_id",
      header: "ID",
      render: (row) => (
        <span className="text-sm tabular-nums text-text-secondary">
          #{row.entity_id}
        </span>
      ),
    },
    {
      key: "new_value",
      header: "Details",
      className: "max-w-[300px]",
      render: (row) => {
        const detail = row.new_value || row.old_value;
        if (!detail) return <span className="text-text-secondary">-</span>;
        try {
          const parsed = JSON.parse(detail);
          const summary = Object.entries(parsed)
            .slice(0, 3)
            .map(([k, v]) => `${k}: ${v}`)
            .join(", ");
          return (
            <span className="text-xs text-text-secondary truncate block max-w-[280px]" title={detail}>
              {summary}
            </span>
          );
        } catch {
          return (
            <span className="text-xs text-text-secondary truncate block max-w-[280px]" title={detail}>
              {detail.slice(0, 80)}
            </span>
          );
        }
      },
    },
  ];

  return (
    <PageLayout
      title="Journal d'audit"
      description="Historique complet des actions effectuees dans le systeme"
      breadcrumb={[
        { label: "Admin", href: "/admin" },
        { label: "Journal d'audit" },
      ]}
      actions={
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-text-secondary" aria-hidden="true" />
          <span className="text-sm text-text-secondary">
            {data ? `${data.total} entrees` : ""}
          </span>
        </div>
      }
    >
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4 mb-6">
        <div>
          <label htmlFor="action-filter" className="block text-sm font-medium text-text-secondary mb-1">
            Action
          </label>
          <select
            id="action-filter"
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              handleFilterChange();
            }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:ring-2 focus:ring-primary focus:outline-none"
          >
            {ACTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="entity-filter" className="block text-sm font-medium text-text-secondary mb-1">
            Entite
          </label>
          <select
            id="entity-filter"
            value={entityFilter}
            onChange={(e) => {
              setEntityFilter(e.target.value);
              handleFilterChange();
            }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:ring-2 focus:ring-primary focus:outline-none"
          >
            {ENTITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="date-from" className="block text-sm font-medium text-text-secondary mb-1">
            Du
          </label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              handleFilterChange();
            }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>

        <div>
          <label htmlFor="date-to" className="block text-sm font-medium text-text-secondary mb-1">
            Au
          </label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              handleFilterChange();
            }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>

        {(actionFilter || entityFilter || dateFrom || dateTo) && (
          <button
            onClick={() => {
              setActionFilter("");
              setEntityFilter("");
              setDateFrom("");
              setDateTo("");
              setPage(1);
            }}
            className="rounded-lg border border-border px-3 py-2 text-sm text-text-secondary hover:bg-gray-100 focus:ring-2 focus:ring-primary focus:outline-none"
          >
            Reinitialiser
          </button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        emptyTitle="Aucune entree d'audit"
        emptyDescription="Aucune action n'a ete enregistree pour les filtres selectionnes."
        page={page}
        pageSize={pageSize}
        total={data?.total}
        onPageChange={setPage}
      />
    </PageLayout>
  );
}
