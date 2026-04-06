"use client";

import { AlertTriangle, XCircle, Info, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { ConsolidationAlert } from "@/lib/types/pec-preparation";

interface AlertPanelProps {
  alerts: ConsolidationAlert[];
  dismissedAlerts?: Set<string>;
  onDismiss?: (alertKey: string) => void;
}

const severityConfig = {
  error: {
    border: "border-red-300",
    bg: "bg-red-50",
    icon: XCircle,
    iconColor: "text-red-600",
    textColor: "text-red-800",
  },
  warning: {
    border: "border-amber-300",
    bg: "bg-amber-50",
    icon: AlertTriangle,
    iconColor: "text-amber-600",
    textColor: "text-amber-800",
  },
  info: {
    border: "border-blue-300",
    bg: "bg-blue-50",
    icon: Info,
    iconColor: "text-blue-600",
    textColor: "text-blue-800",
  },
} as const;

const severityOrder: Record<string, number> = { error: 0, warning: 1, info: 2 };

function alertKey(alert: ConsolidationAlert, idx: number): string {
  return `${alert.severity}_${alert.field}_${idx}`;
}

export function AlertPanel({ alerts, dismissedAlerts, onDismiss }: AlertPanelProps) {
  const sorted = [...alerts].sort(
    (a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9),
  );

  if (sorted.length === 0) {
    return (
      <div className="flex items-center gap-2 py-4 text-emerald-600">
        <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
        <span className="text-sm font-medium">Aucune alerte. Toutes les donnees sont coherentes.</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sorted.map((alert, idx) => {
        const key = alertKey(alert, idx);
        const cfg = severityConfig[alert.severity] ?? severityConfig.info;
        const Icon = cfg.icon;
        const isDismissed = dismissedAlerts?.has(key);

        return (
          <div
            key={key}
            className={cn(
              "flex items-start gap-3 rounded-lg border p-3 transition-opacity",
              cfg.border,
              cfg.bg,
              isDismissed && "opacity-50",
            )}
          >
            <Icon className={cn("h-5 w-5 mt-0.5 shrink-0", cfg.iconColor)} aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className={cn("text-sm font-medium", cfg.textColor)}>{alert.message}</p>
              {alert.sources.length > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  Sources : {alert.sources.join(", ")}
                </p>
              )}
            </div>
            {onDismiss && !isDismissed && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onDismiss(key)}
                aria-label="Marquer comme verifie"
              >
                <CheckCircle2 className="h-3 w-3 mr-1" />
                {"J'ai verifie"}
              </Button>
            )}
            {isDismissed && (
              <span className="text-xs text-emerald-600 font-medium shrink-0 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Verifie
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
