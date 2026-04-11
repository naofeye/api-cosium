"use client";

import { Heart, CheckCircle, AlertCircle, Database, Server, HardDrive } from "lucide-react";
import type { HealthCheckResponse } from "@/lib/types/admin";

const SERVICE_ICONS: Record<string, typeof Database> = { postgres: Database, redis: Server, minio: HardDrive };

interface HealthStatusProps {
  health: HealthCheckResponse | undefined;
}

export function HealthStatus({ health }: HealthStatusProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Heart className="h-5 w-5" /> Sante du systeme
        </h3>
        {health && (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
              health.status === "healthy" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
            }`}
          >
            {health.status === "healthy" ? (
              <CheckCircle className="h-3.5 w-3.5" />
            ) : (
              <AlertCircle className="h-3.5 w-3.5" />
            )}
            {health.status === "healthy" ? "Tous les services operationnels" : "Service(s) degrade(s)"}
          </span>
        )}
      </div>
      {health ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(health.services).map(([name, svc]) => {
            const Icon = SERVICE_ICONS[name] || Server;
            return (
              <div
                key={name}
                className={`flex items-center gap-3 rounded-lg border p-4 ${
                  svc.status === "ok" ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"
                }`}
              >
                <Icon className={`h-5 w-5 ${svc.status === "ok" ? "text-emerald-600" : "text-red-600"}`} />
                <div className="flex-1">
                  <p className="text-sm font-semibold capitalize">{name}</p>
                  <p className="text-xs text-text-secondary">
                    {svc.status === "ok" ? `${svc.response_ms}ms` : svc.error || "Erreur"}
                  </p>
                </div>
                <div className={`h-3 w-3 rounded-full ${svc.status === "ok" ? "bg-emerald-500" : "bg-red-500"}`} />
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-text-secondary">Impossible de charger l&apos;etat des services.</p>
      )}
    </div>
  );
}
