"use client";

import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

interface KPICardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  trend?: { value: number; label?: string };
  color?: "primary" | "success" | "warning" | "danger" | "info";
  className?: string;
}

const colorMap = {
  primary: "border-t-primary",
  success: "border-t-success",
  warning: "border-t-warning",
  danger: "border-t-danger",
  info: "border-t-info",
};

const iconColorMap = {
  primary: "text-primary bg-blue-100 dark:bg-blue-900/30",
  success: "text-success bg-emerald-100 dark:bg-emerald-900/30",
  warning: "text-warning bg-amber-100 dark:bg-amber-900/30",
  danger: "text-danger bg-red-100 dark:bg-red-900/30",
  info: "text-info bg-sky-100 dark:bg-sky-900/30",
};

export function KPICard({ icon: Icon, label, value, trend, color = "primary", className }: KPICardProps) {
  return (
    <div
      className={cn("rounded-xl border border-border bg-bg-card p-6 shadow-sm border-t-[3px] transition-all duration-200 hover:shadow-md hover:-translate-y-0.5", colorMap[color], className)}
    >
      <div className="flex items-center justify-between">
        <div className={cn("rounded-lg p-2", iconColorMap[color])}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        {trend && (
          <span
            className={cn("text-xs font-medium", trend.value >= 0 ? "text-success" : "text-danger")}
            aria-label={`Tendance : ${trend.value >= 0 ? "hausse" : "baisse"} de ${Math.abs(trend.value)}%`}
          >
            {trend.value >= 0 ? "+" : ""}
            {trend.value}%{" "}
            <span className="sr-only">({trend.value >= 0 ? "hausse" : "baisse"})</span>
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold tabular-nums leading-tight">{value}</p>
        <p className="mt-1 text-sm text-text-secondary">{label}</p>
      </div>
    </div>
  );
}
