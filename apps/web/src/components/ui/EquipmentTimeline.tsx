"use client";

import { Glasses, Eye, Sun, Package } from "lucide-react";
import { cn } from "@/lib/utils";

interface EquipmentItem {
  id?: number | string;
  date?: string | null;
  label: string;
  type: "frame" | "lens" | "sun" | "other";
  amount?: number | null;
}

interface EquipmentTimelineProps {
  items: EquipmentItem[];
  className?: string;
}

const TYPE_CONFIG = {
  frame: { icon: Glasses, label: "Monture", color: "text-primary bg-blue-100" },
  lens: { icon: Eye, label: "Verres", color: "text-indigo-600 bg-indigo-100" },
  sun: { icon: Sun, label: "Solaire", color: "text-amber-600 bg-amber-100" },
  other: { icon: Package, label: "Autre", color: "text-gray-600 bg-gray-100" },
} as const;

/**
 * Frise chronologique verticale des equipements optiques achetes.
 */
export function EquipmentTimeline({ items, className }: EquipmentTimelineProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-text-secondary italic">Aucun equipement enregistre.</p>
    );
  }

  // Tri decroissant par date
  const sorted = [...items].sort((a, b) => {
    const da = a.date ? new Date(a.date).getTime() : 0;
    const db = b.date ? new Date(b.date).getTime() : 0;
    return db - da;
  });

  return (
    <ol className={cn("relative border-l-2 border-gray-200 ml-4", className)}>
      {sorted.map((item, i) => {
        const cfg = TYPE_CONFIG[item.type];
        const Icon = cfg.icon;
        return (
          <li key={item.id ?? i} className="pl-6 pb-6 last:pb-0 relative">
            <span
              className={cn(
                "absolute -left-4 top-0 flex h-8 w-8 items-center justify-center rounded-full ring-4 ring-white",
                cfg.color,
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="rounded-lg border border-border bg-bg-card p-3 shadow-sm">
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-sm font-medium text-text-primary truncate">{item.label}</p>
                {item.amount != null && (
                  <span className="text-sm font-semibold tabular-nums">
                    {item.amount.toLocaleString("fr-FR", { minimumFractionDigits: 2 })} EUR
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-center gap-2 text-xs text-text-secondary">
                <span className="font-medium">{cfg.label}</span>
                {item.date && <span>·</span>}
                {item.date && <time>{item.date}</time>}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
