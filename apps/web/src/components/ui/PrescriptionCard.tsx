"use client";

import { Eye, CalendarDays, User } from "lucide-react";
import { cn } from "@/lib/utils";

interface DiopterValues {
  sphere?: number | null;
  cylinder?: number | null;
  axis?: number | null;
  addition?: number | null;
  prism?: number | null;
}

interface PrescriptionCardProps {
  right?: DiopterValues;
  left?: DiopterValues;
  date?: string | null;
  prescriberName?: string | null;
  className?: string;
}

function fmt(value: number | null | undefined, sign = true): string {
  if (value == null) return "—";
  if (!sign) return value.toString();
  return value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}

/**
 * Carte prescription optique : dioptries OD/OG avec format metier standard.
 */
export function PrescriptionCard({
  right = {},
  left = {},
  date,
  prescriberName,
  className,
}: PrescriptionCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-bg-card p-5 shadow-sm",
        className,
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <CalendarDays className="h-4 w-4" aria-hidden="true" />
          <span>{date ?? "Date inconnue"}</span>
        </div>
        {prescriberName && (
          <div className="flex items-center gap-1 text-xs text-text-secondary">
            <User className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="truncate max-w-[140px]">{prescriberName}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <EyeColumn label="OD (droit)" values={right} />
        <EyeColumn label="OG (gauche)" values={left} />
      </div>
    </div>
  );
}

function EyeColumn({ label, values }: { label: string; values: DiopterValues }) {
  return (
    <div className="rounded-lg bg-gray-50 p-3">
      <div className="flex items-center gap-1.5 mb-2">
        <Eye className="h-4 w-4 text-primary" aria-hidden="true" />
        <span className="text-xs font-semibold uppercase tracking-wide text-text-secondary">{label}</span>
      </div>
      <dl className="space-y-1 text-sm tabular-nums">
        <Row label="Sphere" value={fmt(values.sphere)} />
        <Row label="Cylindre" value={fmt(values.cylinder)} />
        <Row label="Axe" value={fmt(values.axis, false)} />
        <Row label="Addition" value={fmt(values.addition)} />
        {values.prism != null && <Row label="Prisme" value={fmt(values.prism)} />}
      </dl>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-text-secondary">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}
