"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { CompletionGauge } from "@/components/pec/CompletionGauge";
import {
  ClipboardCheck,
  CheckCircle,
  AlertTriangle,
  Send,
  ListChecks,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface PecPreparationItem {
  id: number;
  customer_id: number;
  customer_name: string;
  devis_id: number | null;
  status: string;
  completude_score: number;
  errors_count: number;
  warnings_count: number;
  created_at: string | null;
}

interface PecDashboardData {
  items: PecPreparationItem[];
  total: number;
  counts: Record<string, number>;
}

const STATUS_LABELS: Record<string, string> = {
  en_preparation: "En preparation",
  prete: "Prete",
  soumise: "Soumise",
};

const STATUS_COLORS: Record<string, string> = {
  en_preparation: "bg-amber-100 text-amber-800",
  prete: "bg-emerald-100 text-emerald-800",
  soumise: "bg-blue-100 text-blue-800",
};

const STATUS_OPTIONS = [
  { value: "", label: "Tous les statuts" },
  { value: "en_preparation", label: "En preparation" },
  { value: "prete", label: "Prete" },
  { value: "soumise", label: "Soumise" },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  try {
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "-";
  }
}

export default function PecDashboardPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    if (statusFilter) params.set("status", statusFilter);
    return params.toString();
  }, [page, statusFilter]);

  const { data, error, isLoading, mutate } = useSWR<PecDashboardData>(
    `/pec-preparations?${queryParams}`,
    { refreshInterval: 30000 }
  );

  const counts = data?.counts ?? {};
  const totalAll =
    (counts["en_preparation"] ?? 0) +
    (counts["prete"] ?? 0) +
    (counts["soumise"] ?? 0);
  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  return (
    <PageLayout
      title="Assistance PEC"
      description="Tableau de bord des preparations de prise en charge"
      breadcrumb={[{ label: "Dashboard", href: "/dashboard" }, { label: "Assistance PEC" }]}
    >
      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard
          icon={ListChecks}
          label="Total preparations"
          value={totalAll}
          color="primary"
        />
        <KPICard
          icon={CheckCircle}
          label="Pretes"
          value={counts["prete"] ?? 0}
          color="success"
        />
        <KPICard
          icon={AlertTriangle}
          label="En preparation"
          value={counts["en_preparation"] ?? 0}
          color="warning"
        />
        <KPICard
          icon={Send}
          label="Soumises"
          value={counts["soumise"] ?? 0}
          color="info"
        />
      </div>

      {/* Filter */}
      <div className="flex items-center gap-4 mb-4">
        <label htmlFor="status-filter" className="text-sm font-medium text-text-secondary">
          Filtrer par statut
        </label>
        <select
          id="status-filter"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:ring-2 focus:ring-primary focus:outline-none"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Table / states */}
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
        <>
          <div className="overflow-x-auto rounded-xl border border-border bg-bg-card shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50 text-left">
                  <th className="px-4 py-3 font-semibold text-text-secondary">Client</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary">Statut</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary">Score</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary text-center">Erreurs</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary text-center">Alertes</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary">Date</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-border last:border-0 hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() =>
                      router.push(
                        `/clients/${item.customer_id}/pec-preparation/${item.id}`
                      )
                    }
                  >
                    <td className="px-4 py-3 font-medium text-text-primary">
                      {item.customer_name}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          STATUS_COLORS[item.status] ?? "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {STATUS_LABELS[item.status] ?? item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 w-48">
                      <CompletionGauge score={item.completude_score} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.errors_count > 0 ? (
                        <span className="inline-flex items-center justify-center rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-semibold tabular-nums">
                          {item.errors_count}
                        </span>
                      ) : (
                        <span className="text-text-secondary">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.warnings_count > 0 ? (
                        <span className="inline-flex items-center justify-center rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-semibold tabular-nums">
                          {item.warnings_count}
                        </span>
                      ) : (
                        <span className="text-text-secondary">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-text-secondary">
                      {formatDate(item.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(
                            `/clients/${item.customer_id}/pec-preparation/${item.id}`
                          );
                        }}
                        className="text-primary hover:underline text-sm font-medium"
                        aria-label={`Voir la preparation PEC de ${item.customer_name}`}
                      >
                        Voir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-text-secondary">
                {data.total} preparation{data.total > 1 ? "s" : ""} au total
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Page precedente"
                >
                  <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                  Precedent
                </button>
                <span className="text-sm text-text-secondary tabular-nums">
                  Page {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Page suivante"
                >
                  Suivant
                  <ChevronRight className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}
