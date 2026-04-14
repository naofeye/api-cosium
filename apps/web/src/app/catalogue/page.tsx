"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Glasses, Sparkles, Search } from "lucide-react";
import { formatMoney } from "@/lib/format";

interface Frame {
  cosium_id: number | null;
  brand: string | null;
  model: string | null;
  color: string | null;
  material: string | null;
  style: string | null;
  size: number | null;
  nose_width: number | null;
  arm_size: number | null;
  price: number | null;
}

interface Lens {
  cosium_id: number | null;
  brand: string | null;
  model: string | null;
  price: number | null;
  material: string | null;
  index: number | null;
  treatment: string | null;
  tint: string | null;
  photochromic: boolean | null;
  has_options: boolean;
}

type CatalogTab = "frames" | "lenses";

function FramesGrid({ search }: { search: string }) {
  const { data, error, isLoading, mutate } = useSWR<Frame[]>("/cosium/catalog/frames?page_size=100");

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!search.trim()) return data;
    const q = search.toLowerCase();
    return data.filter((f) =>
      [f.brand, f.model, f.color, f.material, f.style].some((v) => v && v.toLowerCase().includes(q))
    );
  }, [data, search]);

  if (isLoading) return <LoadingState text="Chargement du catalogue montures..." />;
  if (error) return <ErrorState message="Impossible de charger les montures Cosium" onRetry={() => mutate()} />;
  if (!data || data.length === 0) {
    return <EmptyState title="Catalogue vide" description="Aucune monture disponible dans le catalogue Cosium." />;
  }
  if (filtered.length === 0) {
    return <EmptyState title="Aucun resultat" description={`Aucune monture ne correspond a "${search}".`} />;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {filtered.map((f, idx) => (
        <div
          key={f.cosium_id ?? idx}
          className="rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex justify-between items-start mb-3">
            <div>
              <p className="font-semibold text-text-primary">{f.brand ?? "?"}</p>
              <p className="text-sm text-text-secondary">{f.model ?? "Sans modele"}</p>
            </div>
            <span className="text-base font-bold text-primary tabular-nums">
              {f.price !== null ? formatMoney(f.price) : "-"}
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5 text-xs">
            {f.color && <span className="rounded bg-gray-100 px-2 py-0.5">{f.color}</span>}
            {f.material && <span className="rounded bg-blue-50 text-blue-700 px-2 py-0.5">{f.material}</span>}
            {f.style && <span className="rounded bg-purple-50 text-purple-700 px-2 py-0.5">{f.style}</span>}
          </div>
          {(f.size || f.nose_width || f.arm_size) && (
            <p className="mt-2 text-xs text-text-secondary tabular-nums">
              {f.size ?? "?"}-{f.nose_width ?? "?"}-{f.arm_size ?? "?"} mm
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function LensesGrid({ search }: { search: string }) {
  const { data, error, isLoading, mutate } = useSWR<Lens[]>("/cosium/catalog/lenses?page_size=100");

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!search.trim()) return data;
    const q = search.toLowerCase();
    return data.filter((l) =>
      [l.brand, l.model, l.material, l.treatment, l.tint].some((v) => v && v.toLowerCase().includes(q))
    );
  }, [data, search]);

  if (isLoading) return <LoadingState text="Chargement du catalogue verres..." />;
  if (error) return <ErrorState message="Impossible de charger les verres Cosium" onRetry={() => mutate()} />;
  if (!data || data.length === 0) {
    return <EmptyState title="Catalogue vide" description="Aucun verre disponible dans le catalogue Cosium." />;
  }
  if (filtered.length === 0) {
    return <EmptyState title="Aucun resultat" description={`Aucun verre ne correspond a "${search}".`} />;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {filtered.map((l, idx) => (
        <div
          key={l.cosium_id ?? idx}
          className="rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:shadow-md transition-all"
        >
          <div className="flex justify-between items-start mb-3">
            <div>
              <p className="font-semibold text-text-primary">{l.brand ?? "?"}</p>
              <p className="text-sm text-text-secondary">{l.model ?? "Sans modele"}</p>
            </div>
            <span className="text-base font-bold text-primary tabular-nums">
              {l.price !== null ? formatMoney(l.price) : "-"}
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5 text-xs">
            {l.material && <span className="rounded bg-gray-100 px-2 py-0.5">{l.material}</span>}
            {l.index !== null && <span className="rounded bg-blue-50 text-blue-700 px-2 py-0.5 tabular-nums">Indice {l.index}</span>}
            {l.treatment && <span className="rounded bg-emerald-50 text-emerald-700 px-2 py-0.5">{l.treatment}</span>}
            {l.tint && <span className="rounded bg-amber-50 text-amber-700 px-2 py-0.5">{l.tint}</span>}
            {l.photochromic && <span className="rounded bg-purple-50 text-purple-700 px-2 py-0.5">Photochromique</span>}
          </div>
          {l.has_options && (
            <p className="mt-2 text-xs text-text-secondary italic">Options disponibles</p>
          )}
        </div>
      ))}
    </div>
  );
}

export default function CataloguePage() {
  const [tab, setTab] = useState<CatalogTab>("frames");
  const [search, setSearch] = useState("");

  return (
    <PageLayout
      title="Catalogue optique"
      description="Montures et verres disponibles dans le catalogue Cosium (lecture seule)"
      breadcrumb={[{ label: "Cosium" }, { label: "Catalogue" }]}
    >
      <div className="border-b border-border mb-6">
        <div className="flex gap-0" role="tablist" aria-label="Sections du catalogue">
          <button
            role="tab"
            aria-selected={tab === "frames"}
            onClick={() => setTab("frames")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === "frames"
                ? "border-primary text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            <Glasses className="h-4 w-4" />
            Montures
          </button>
          <button
            role="tab"
            aria-selected={tab === "lenses"}
            onClick={() => setTab("lenses")}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === "lenses"
                ? "border-primary text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            <Sparkles className="h-4 w-4" />
            Verres
          </button>
        </div>
      </div>

      <div className="mb-4 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" aria-hidden="true" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={tab === "frames" ? "Rechercher monture (marque, modele, couleur, materiau, style)..." : "Rechercher verre (marque, modele, materiau, traitement, teinte)..."}
          className="w-full max-w-xl pl-10 pr-3 py-2 rounded-lg border border-border bg-bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      {tab === "frames" && <FramesGrid search={search} />}
      {tab === "lenses" && <LensesGrid search={search} />}
    </PageLayout>
  );
}
