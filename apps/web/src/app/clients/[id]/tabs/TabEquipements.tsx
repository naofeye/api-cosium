"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Glasses } from "lucide-react";

interface EquipmentItem {
  prescription_id: number;
  prescription_date: string | null;
  label: string;
  brand: string;
  type: string;
}

interface TabEquipementsProps {
  equipments: EquipmentItem[];
}

export function TabEquipements({ equipments }: TabEquipementsProps) {
  if (equipments.length === 0) {
    return (
      <EmptyState
        title="Aucun equipement"
        description="Aucun equipement optique trouve dans les ordonnances de ce client."
      />
    );
  }

  return (
    <div className="space-y-3">
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
