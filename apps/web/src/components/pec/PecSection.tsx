"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, XCircle, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PecSectionProps {
  title: string;
  icon: LucideIcon;
  status: "ok" | "warning" | "error";
  defaultOpen?: boolean;
  children: ReactNode;
}

const statusConfig = {
  ok: {
    border: "border-emerald-200",
    bg: "bg-emerald-50",
    icon: CheckCircle2,
    iconColor: "text-emerald-600",
    label: "Complet",
  },
  warning: {
    border: "border-amber-200",
    bg: "bg-amber-50",
    icon: AlertTriangle,
    iconColor: "text-amber-600",
    label: "Attention",
  },
  error: {
    border: "border-red-200",
    bg: "bg-red-50",
    icon: XCircle,
    iconColor: "text-red-600",
    label: "Erreur",
  },
} as const;

export function PecSection({ title, icon: Icon, status, defaultOpen = true, children }: PecSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const cfg = statusConfig[status];
  const StatusIcon = cfg.icon;

  return (
    <div className={cn("rounded-xl border shadow-sm", cfg.border)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center justify-between px-5 py-4 rounded-t-xl transition-colors",
          cfg.bg,
          "hover:opacity-90",
        )}
        aria-expanded={open}
        aria-label={`${title} - ${cfg.label}`}
      >
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-gray-600" aria-hidden="true" />
          <span className="text-sm font-semibold text-gray-900">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <StatusIcon className={cn("h-4 w-4", cfg.iconColor)} aria-label={cfg.label} />
          {open ? (
            <ChevronDown className="h-4 w-4 text-gray-400" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" aria-hidden="true" />
          )}
        </div>
      </button>
      {open && (
        <div className="px-5 py-4 bg-white rounded-b-xl">
          {children}
        </div>
      )}
    </div>
  );
}
