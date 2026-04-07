"use client";

import useSWR from "swr";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { BatchOperation } from "@/lib/types";
import { Plus } from "lucide-react";

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  try {
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "-";
  }
}

export default function BatchHistoriquePage() {
  const router = useRouter();
  const { data, error, isLoading } = useSWR<BatchOperation[]>("/batch/operations");

  return (
    <PageLayout
      title="Historique des lots Journees entreprise"
      description="Tous les traitements batch passes"
      breadcrumb={[
        { label: "Journees entreprise", href: "/operations-batch" },
        { label: "Historique" },
      ]}
      actions={
        <Link
          href="/operations-batch"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Nouveau lot
        </Link>
      }
    >
      {isLoading && <LoadingState text="Chargement de l'historique..." />}

      {error && (
        <ErrorState
          message="Impossible de charger l'historique des lots."
          onRetry={() => window.location.reload()}
        />
      )}

      {!isLoading && !error && data && data.length === 0 && (
        <EmptyState
          title="Aucun lot"
          description="Aucun traitement batch n'a ete effectue pour le moment."
          action={
            <Link
              href="/operations-batch"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              Creer un lot
            </Link>
          }
        />
      )}

      {!isLoading && !error && data && data.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-gray-50 text-left">
                <th className="px-4 py-3 font-medium text-text-secondary">Date</th>
                <th className="px-4 py-3 font-medium text-text-secondary">Code marketing</th>
                <th className="px-4 py-3 font-medium text-text-secondary">Label</th>
                <th className="px-4 py-3 font-medium text-text-secondary">Clients</th>
                <th className="px-4 py-3 font-medium text-text-secondary">Prets</th>
                <th className="px-4 py-3 font-medium text-text-secondary">Incomplets</th>
                <th className="px-4 py-3 font-medium text-text-secondary">Statut</th>
              </tr>
            </thead>
            <tbody>
              {data.map((op) => (
                <tr
                  key={op.id}
                  onClick={() => router.push(`/operations-batch/${op.id}`)}
                  className="border-b border-border last:border-0 hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-4 py-3 text-text-primary">{formatDate(op.started_at)}</td>
                  <td className="px-4 py-3 font-medium">{op.marketing_code}</td>
                  <td className="px-4 py-3 text-text-secondary">{op.label || "-"}</td>
                  <td className="px-4 py-3 tabular-nums">{op.total_clients}</td>
                  <td className="px-4 py-3 tabular-nums text-emerald-600">{op.clients_prets}</td>
                  <td className="px-4 py-3 tabular-nums text-amber-600">{op.clients_incomplets}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={op.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageLayout>
  );
}
