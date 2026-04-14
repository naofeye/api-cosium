"use client";

import useSWR from "swr";
import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Glasses, FolderOpen, Eye } from "lucide-react";

interface EquipmentItem {
  prescription_id: number;
  prescription_date: string | null;
  label: string;
  brand: string;
  type: string;
}

interface SpectacleFileMeta {
  cosium_id: number | null;
  has_diopters: boolean;
  has_selection: boolean;
  has_doctor_address: boolean;
  creation_date: string | null;
}

interface TabEquipementsProps {
  equipments: EquipmentItem[];
  cosiumId?: string | number | null;
}

function SpectaclesLive({ cosiumId }: { cosiumId: string | number }) {
  const { data, error } = useSWR<SpectacleFileMeta[]>(
    `/cosium/spectacles/customer/${cosiumId}`,
    { shouldRetryOnError: false },
  );

  if (error) return null;  // Silent fail — equipment cache reste affiche
  if (!data || data.length === 0) return null;

  return (
    <section className="mb-6">
      <div className="mb-3 flex items-center gap-2">
        <FolderOpen className="h-5 w-5 text-purple-600" />
        <h3 className="text-base font-semibold text-text-primary">Dossiers lunettes Cosium en cours</h3>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">{data.length}</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.map((f) => (
          <div key={f.cosium_id} className="rounded-xl border border-purple-200 bg-purple-50/40 p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-text-secondary">N° {f.cosium_id ?? "?"}</span>
              {f.creation_date && (
                <span className="text-xs text-text-secondary">
                  <DateDisplay date={f.creation_date} />
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 text-xs">
              {f.has_diopters && (
                <span className="inline-flex items-center gap-1 rounded bg-blue-100 text-blue-700 px-2 py-0.5">
                  <Eye className="h-3 w-3" /> Dioptries
                </span>
              )}
              {f.has_selection && (
                <span className="rounded bg-emerald-100 text-emerald-700 px-2 py-0.5">Selection</span>
              )}
              {f.has_doctor_address && (
                <span className="rounded bg-amber-100 text-amber-700 px-2 py-0.5">Prescripteur</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function TabEquipements({ equipments, cosiumId }: TabEquipementsProps) {
  if (equipments.length === 0 && !cosiumId) {
    return (
      <EmptyState
        title="Aucun equipement"
        description="Aucun equipement optique trouve dans les ordonnances de ce client."
      />
    );
  }

  return (
    <div className="space-y-3">
      {cosiumId && <SpectaclesLive cosiumId={cosiumId} />}
      {equipments.length === 0 && (
        <p className="text-sm text-text-secondary italic">Aucun equipement historique en cache local.</p>
      )}
      {equipments.map((eq, idx) => (
        <div
          key={`${eq.prescription_id}-${idx}`}
          className="flex items-start gap-4 rounded-xl border border-border bg-bg-card p-4 shadow-sm"
        >
          <Glasses className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" aria-hidden="true" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {eq.label || "Equipement"}
            </p>
            <div className="flex flex-wrap gap-3 mt-1 text-xs text-text-secondary">
              {eq.brand && (
                <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-blue-700 border border-blue-200">
                  {eq.brand}
                </span>
              )}
              {eq.type && (
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-gray-700">
                  {eq.type}
                </span>
              )}
              {eq.prescription_date && (
                <span>
                  <DateDisplay date={eq.prescription_date} />
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
