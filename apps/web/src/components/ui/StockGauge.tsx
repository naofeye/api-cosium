import { cn } from "@/lib/utils";

interface StockGaugeProps {
  available: number;
  threshold?: number;
  label?: string;
  className?: string;
}

/**
 * Jauge stock avec code couleur : vert si >= threshold, orange si moitie, rouge si bas.
 */
export function StockGauge({ available, threshold = 10, label, className }: StockGaugeProps) {
  const ratio = Math.min(1, Math.max(0, available / (threshold * 2)));
  const percentage = Math.round(ratio * 100);
  const level =
    available === 0
      ? "rupture"
      : available < threshold / 2
        ? "critique"
        : available < threshold
          ? "bas"
          : "ok";

  const palette = {
    rupture: { bar: "bg-red-600", text: "text-red-700", bg: "bg-red-100" },
    critique: { bar: "bg-red-500", text: "text-red-600", bg: "bg-red-50" },
    bas: { bar: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50" },
    ok: { bar: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
  }[level];

  const statusLabel = {
    rupture: "Rupture",
    critique: "Stock critique",
    bas: "Stock bas",
    ok: "En stock",
  }[level];

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-baseline justify-between gap-2">
        <span className={cn("text-xs font-medium uppercase tracking-wide", palette.text)}>
          {label ?? statusLabel}
        </span>
        <span className="text-sm font-semibold tabular-nums">{available}</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={available}
        aria-valuemin={0}
        aria-valuemax={threshold * 2}
        aria-label={`Stock ${statusLabel}: ${available} unites`}
        className={cn("h-2 w-full rounded-full overflow-hidden", palette.bg)}
      >
        <div
          className={cn("h-full transition-all duration-300", palette.bar)}
          style={{ width: `${Math.max(4, percentage)}%` }}
        />
      </div>
    </div>
  );
}
