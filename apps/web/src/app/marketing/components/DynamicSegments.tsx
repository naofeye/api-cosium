"use client";

import useSWR from "swr";
import { Sparkles } from "lucide-react";
import { formatMoney } from "@/lib/format";

interface DynamicSegment {
  key: string;
  label: string;
  description: string;
  count: number;
  ca?: number;
  color: string;
}

const COLOR_MAP: Record<string, { bg: string; text: string; border: string }> = {
  emerald: { bg: "bg-emerald-50", text: "text-emerald-900", border: "border-emerald-200" },
  purple: { bg: "bg-purple-50", text: "text-purple-900", border: "border-purple-200" },
  gray: { bg: "bg-gray-50", text: "text-gray-900", border: "border-gray-200" },
  red: { bg: "bg-red-50", text: "text-red-900", border: "border-red-200" },
  blue: { bg: "bg-blue-50", text: "text-blue-900", border: "border-blue-200" },
};

export function DynamicSegmentsPanel() {
  const { data, error, isLoading } = useSWR<DynamicSegment[]>(
    "/analytics/dynamic-segments",
    { refreshInterval: 600000 },
  );

  if (isLoading || error || !data || data.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
          Segments suggeres (live Cosium)
        </h3>
        <span className="ml-auto text-[10px] text-text-secondary italic">
          Cliquez pour creer une campagne ciblee
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        {data.map((seg) => {
          const c = COLOR_MAP[seg.color] ?? COLOR_MAP.gray;
          return (
            <div
              key={seg.key}
              className={`rounded-lg border ${c.border} ${c.bg} p-3 cursor-pointer hover:shadow-md transition-shadow`}
              title={seg.description}
            >
              <p className={`text-xs font-semibold uppercase tracking-wide ${c.text}`}>{seg.label}</p>
              <div className="mt-2 flex items-baseline gap-2">
                <span className={`text-2xl font-bold tabular-nums ${c.text}`}>{seg.count.toLocaleString("fr-FR")}</span>
                <span className="text-xs text-text-secondary">clients</span>
              </div>
              {seg.ca !== undefined && (
                <p className="mt-1 text-xs text-text-secondary tabular-nums">CA total : {formatMoney(seg.ca)}</p>
              )}
              <p className="mt-1.5 text-[10px] text-text-secondary italic line-clamp-2">{seg.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
