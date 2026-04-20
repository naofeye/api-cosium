"use client";

import { useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { SearchInput } from "@/components/ui/SearchInput";
import { StockGauge } from "@/components/ui/StockGauge";
import { KPICard } from "@/components/ui/KPICard";
import { useCosiumProducts } from "@/lib/hooks/use-api";
import { Package, AlertTriangle, CheckCircle } from "lucide-react";
import type { CosiumProduct } from "@/lib/types";

const LOW_STOCK_THRESHOLD = 5;

export default function StockPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const { data, error, isLoading, mutate } = useCosiumProducts({
    page,
    page_size: 25,
    search: search || undefined,
  });

  const items: (CosiumProduct & { stock?: number })[] = data?.items ?? [];
  const ruptures = items.filter((p) => (p.stock ?? 0) === 0).length;
  const bas = items.filter((p) => (p.stock ?? 0) > 0 && (p.stock ?? 0) < LOW_STOCK_THRESHOLD).length;
  const ok = items.length - ruptures - bas;

  return (
    <ErrorBoundary name="Stock">
    <PageLayout
      title="Stock"
      description="Catalogue produits Cosium avec indicateurs de disponibilite"
      breadcrumb={[{ label: "Stock" }]}
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KPICard icon={Package} label="Produits affiches" value={items.length} color="primary" />
        <KPICard icon={CheckCircle} label="En stock" value={ok} color="success" />
        <KPICard icon={AlertTriangle} label="Stock bas" value={bas} color="warning" />
        <KPICard icon={AlertTriangle} label="Ruptures" value={ruptures} color="danger" />
      </div>

      <div className="mb-6">
        <SearchInput
          placeholder="Rechercher un produit (nom, code, EAN)..."
          onSearch={(q) => {
            setSearch(q);
            setPage(1);
          }}
        />
      </div>

      {isLoading ? (
        <LoadingState text="Chargement du stock..." />
      ) : error ? (
        <ErrorState message="Impossible de charger le stock." onRetry={() => mutate()} />
      ) : items.length === 0 ? (
        <EmptyState
          title="Aucun produit"
          description="Aucun produit ne correspond a votre recherche ou le catalogue n'a pas ete synchronise."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((p) => (
            <div
              key={p.cosium_id}
              className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex flex-col gap-3"
            >
              <div>
                <p className="text-sm font-medium text-text-primary line-clamp-2">{p.label}</p>
                <p className="font-mono text-xs text-text-secondary mt-0.5">{p.code ?? p.ean_code}</p>
                {p.family_type && (
                  <span className="inline-block mt-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{p.family_type}</span>
                )}
              </div>
              <div className="mt-auto">
                <StockGauge available={p.stock ?? 0} threshold={LOW_STOCK_THRESHOLD} />
                <div className="flex items-baseline justify-between mt-2 text-sm">
                  <span className="text-text-secondary">Prix</span>
                  <span className="font-semibold tabular-nums">
                    {(p.price ?? 0).toLocaleString("fr-FR", { minimumFractionDigits: 2 })} EUR
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {data?.total && data.total > 25 && (
        <div className="mt-6 flex items-center justify-between text-sm text-text-secondary">
          <span>Page {page} sur {Math.ceil(data.total / 25)}</span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg border border-border px-3 py-2 min-h-[44px] hover:bg-gray-50 disabled:opacity-40"
            >
              Precedent
            </button>
            <button
              disabled={page * 25 >= (data.total ?? 0)}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-border px-3 py-2 min-h-[44px] hover:bg-gray-50 disabled:opacity-40"
            >
              Suivant
            </button>
          </div>
        </div>
      )}
    </PageLayout>
    </ErrorBoundary>
  );
}
