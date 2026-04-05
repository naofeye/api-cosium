"use client";

import { useState, useCallback } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { useCosiumCalendarEvents } from "@/lib/hooks/use-api";
import { Calendar } from "lucide-react";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import type { CosiumCalendarEvent } from "@/lib/types";

function eventStatusBadge(event: CosiumCalendarEvent) {
  if (event.canceled) return <StatusBadge status="refuse" label="Annule" />;
  if (event.missed) return <StatusBadge status="retard" label="Absent" />;
  if (event.status === "CONFIRMED") return <StatusBadge status="acceptee" label="Confirme" />;
  return <StatusBadge status="en_attente" label={event.status || "Inconnu"} />;
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

export default function AgendaPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data, error, isLoading, mutate } = useCosiumCalendarEvents({
    page,
    page_size: 25,
    search: search || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const columns: Column<CosiumCalendarEvent>[] = [
    {
      key: "start_date",
      header: "Date",
      sortable: true,
      render: (row) =>
        row.start_date ? <DateDisplay date={row.start_date} /> : <span className="text-text-secondary">-</span>,
    },
    {
      key: "time",
      header: "Heure",
      render: (row) => (
        <span className="font-mono text-sm">
          {formatTime(row.start_date)}
          {row.end_date ? ` - ${formatTime(row.end_date)}` : ""}
        </span>
      ),
    },
    {
      key: "customer_fullname",
      header: "Client",
      sortable: true,
      render: (row) => row.customer_fullname || <span className="text-text-secondary">-</span>,
    },
    {
      key: "category_name",
      header: "Categorie",
      render: (row) => (
        <span className="inline-flex items-center gap-1.5">
          {row.category_color && (
            <span
              className="inline-block h-3 w-3 rounded-full shrink-0"
              style={{ backgroundColor: row.category_color }}
              aria-hidden="true"
            />
          )}
          {row.category_name || "-"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Statut",
      render: (row) => eventStatusBadge(row),
    },
    {
      key: "observation",
      header: "Observation",
      render: (row) => (
        <span className="text-sm text-text-secondary truncate max-w-[200px] block" title={row.observation}>
          {row.observation || "-"}
        </span>
      ),
    },
    {
      key: "site_name",
      header: "Site",
      render: (row) => row.site_name || "-",
    },
  ];

  return (
    <PageLayout
      title="Agenda Cosium"
      description={`${data?.total ?? 0} rendez-vous synchronises`}
      breadcrumb={[{ label: "Agenda" }]}
    >
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher un client..." onSearch={handleSearch} />
        <div className="flex items-center gap-2">
          <label htmlFor="date-from" className="text-sm text-text-secondary">Du</label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="date-to" className="text-sm text-text-secondary">Au</label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
            className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
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
        emptyTitle="Aucun rendez-vous"
        emptyDescription="Synchronisez votre agenda Cosium depuis la page Admin."
        emptyIcon={Calendar}
        emptyAction={
          <Link href="/admin">
            <Button variant="outline">Synchroniser Cosium</Button>
          </Link>
        }
      />
    </PageLayout>
  );
}
