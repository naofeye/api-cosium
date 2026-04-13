"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";

import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

import { PecKpiCards } from "./components/PecKpiCards";
import { PecToolbar } from "./components/PecToolbar";
import { PecPreparationsTable } from "./components/PecPreparationsTable";
import { useExportXlsx } from "./hooks/useExportXlsx";
import type { PecDashboardData } from "./types";

const PAGE_SIZE = 25;

export default function PecDashboardPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(PAGE_SIZE));
    if (statusFilter) params.set("status", statusFilter);
    return params.toString();
  }, [page, statusFilter]);

  const { data, error, isLoading, mutate } = useSWR<PecDashboardData>(
    `/pec-preparations?${queryParams}`,
    { refreshInterval: 30000 },
  );

  const { exporting, exportXlsx } = useExportXlsx(statusFilter);

  return (
    <PageLayout
      title="Assistance PEC"
      description="Tableau de bord des preparations de prise en charge"
      breadcrumb={[{ label: "Dashboard", href: "/dashboard" }, { label: "Assistance PEC" }]}
    >
      <PecKpiCards counts={data?.counts ?? {}} />

      <PecToolbar
        statusFilter={statusFilter}
        onChangeStatus={(s) => { setStatusFilter(s); setPage(1); }}
        onExport={exportXlsx}
        exporting={exporting}
      />

      {isLoading ? (
        <LoadingState text="Chargement des preparations PEC..." />
      ) : error ? (
        <ErrorState message={error.message} onRetry={() => mutate()} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="Aucune preparation PEC"
          description="Les preparations apparaitront ici une fois creees depuis la fiche client."
        />
      ) : (
        <PecPreparationsTable
          items={data.items}
          total={data.total}
          page={page}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      )}
    </PageLayout>
  );
}
