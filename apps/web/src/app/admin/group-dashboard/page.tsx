"use client";

import useSWR from "swr";
import Link from "next/link";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatMoney } from "@/lib/format";
import { Building2, Trophy } from "lucide-react";

interface TenantKPI {
  tenant_id: number;
  tenant_name: string;
  tenant_slug: string;
  ca_30d: number;
  nb_invoices_30d: number;
  panier_moyen: number;
  outstanding_total: number;
  nb_customers: number;
}

export default function GroupDashboardPage() {
  const { data, error, isLoading, mutate } = useSWR<TenantKPI[]>(
    "/analytics/group-comparison",
    { refreshInterval: 300000 },
  );

  return (
    <PageLayout
      title="Tableau de bord groupe"
      description="Comparatif KPIs entre tous les magasins (CA 30 derniers jours)"
      breadcrumb={[{ label: "Admin", href: "/admin" }, { label: "Comparatif magasins" }]}
    >
      {isLoading && <LoadingState text="Chargement comparatif magasins..." />}
      {error && <ErrorState message="Impossible de charger le comparatif" onRetry={() => mutate()} />}
      {data && data.length === 0 && <EmptyState title="Aucun magasin actif" description="Aucun tenant actif a comparer." />}
      {data && data.length > 0 && (
        <>
          <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="h-5 w-5 text-primary" />
              <span className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
                {data.length} magasin{data.length > 1 ? "s" : ""} actif{data.length > 1 ? "s" : ""}
              </span>
            </div>
            <p className="text-2xl font-bold tabular-nums text-text-primary">
              {formatMoney(data.reduce((s, t) => s + t.ca_30d, 0))} <span className="text-sm font-normal text-text-secondary">CA total 30j</span>
            </p>
          </div>
          <div className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-text-secondary font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">#</th>
                  <th className="px-4 py-3 text-left">Magasin</th>
                  <th className="px-4 py-3 text-right">CA 30j</th>
                  <th className="px-4 py-3 text-right">Nb factures</th>
                  <th className="px-4 py-3 text-right">Panier moyen</th>
                  <th className="px-4 py-3 text-right">Encours</th>
                  <th className="px-4 py-3 text-right">Clients</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.map((t, idx) => (
                  <tr key={t.tenant_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {idx === 0 ? (
                        <span className="inline-flex items-center gap-1 text-amber-700 font-bold">
                          <Trophy className="h-4 w-4" />
                          1
                        </span>
                      ) : (
                        <span className="text-text-secondary tabular-nums">{idx + 1}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-text-primary">{t.tenant_name}</p>
                      <p className="text-xs text-text-secondary">{t.tenant_slug}</p>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold">{formatMoney(t.ca_30d)}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{t.nb_invoices_30d.toLocaleString("fr-FR")}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{formatMoney(t.panier_moyen)}</td>
                    <td className={`px-4 py-3 text-right tabular-nums ${t.outstanding_total > 0 ? "text-red-700 font-semibold" : "text-emerald-700"}`}>
                      {formatMoney(t.outstanding_total)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{t.nb_customers.toLocaleString("fr-FR")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </PageLayout>
  );
}
