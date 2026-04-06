"use client";

import { cn } from "@/lib/utils";

interface CompletionGaugeProps {
  score: number;
  className?: string;
}

function getColor(score: number): string {
  if (score < 50) return "bg-red-500";
  if (score < 80) return "bg-amber-500";
  return "bg-emerald-500";
}

function getTextColor(score: number): string {
  if (score < 50) return "text-red-700";
  if (score < 80) return "text-amber-700";
  return "text-emerald-700";
}

export function CompletionGauge({ score, className }: CompletionGaugeProps) {
  const pct = Math.min(100, Math.max(0, Math.round(score)));

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`Score de completude : ${pct}%`}>
        <div
          className={cn("h-full rounded-full transition-all duration-500", getColor(pct))}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn("text-sm font-semibold tabular-nums min-w-[3rem] text-right", getTextColor(pct))}>
        {pct} %
      </span>
    </div>
  );
}
