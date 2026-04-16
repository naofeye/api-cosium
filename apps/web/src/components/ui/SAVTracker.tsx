"use client";

import { Check, Circle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface SAVStep {
  label: string;
  status: "done" | "current" | "pending";
  date?: string;
}

interface SAVTrackerProps {
  steps: SAVStep[];
  className?: string;
}

/**
 * Stepper horizontal pour workflow SAV.
 * Affichage responsive : horizontal desktop, vertical mobile.
 */
export function SAVTracker({ steps, className }: SAVTrackerProps) {
  return (
    <ol
      className={cn("flex flex-col sm:flex-row gap-3 sm:gap-0", className)}
      aria-label="Progression du dossier SAV"
    >
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        const iconBg =
          step.status === "done"
            ? "bg-emerald-500 text-white"
            : step.status === "current"
              ? "bg-blue-500 text-white"
              : "bg-gray-200 text-gray-400";
        const labelColor =
          step.status === "done"
            ? "text-emerald-700"
            : step.status === "current"
              ? "text-blue-700 font-semibold"
              : "text-gray-500";
        const Icon = step.status === "done" ? Check : step.status === "current" ? Clock : Circle;
        return (
          <li key={step.label} className="flex sm:flex-1 items-start sm:items-center sm:flex-col gap-3 sm:gap-1 relative">
            <div className={cn("flex h-8 w-8 flex-none items-center justify-center rounded-full", iconBg)}>
              <Icon className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="flex-1 sm:text-center">
              <p className={cn("text-sm", labelColor)}>{step.label}</p>
              {step.date && <p className="text-xs text-text-secondary mt-0.5">{step.date}</p>}
            </div>
            {!isLast && (
              <span
                aria-hidden="true"
                className="hidden sm:block absolute left-[calc(50%+1rem)] top-4 -translate-y-1/2 h-px w-[calc(100%-2rem)] bg-gray-200"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
