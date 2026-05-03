"use client";

import useSWR from "swr";
import { Activity, Database, Inbox, Server } from "lucide-react";

import { fetchJson } from "@/lib/api";

interface HealthDetail {
  status: string;
  version: string;
  uptime_seconds: number;
  services: Record<string, { status: string; response_ms?: number; error?: string }>;
  db_pool: {
    size?: number | null;
    checked_in?: number | null;
    checked_out?: number | null;
    overflow?: number | null;
    error?: string;
  };
  celery: {
    queues?: Record<string, number>;
    error?: string;
  };
  runtime: {
    python: string;
    platform: string;
    fastapi: string;
    postgres: string;
  };
}

const fetcher = <T,>(url: string) => fetchJson<T>(url);

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}j ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}min`;
  return `${minutes}min`;
}

/**
 * Carte sante systeme enrichie avec auto-refresh 10s. Etend HealthStatus
 * existant avec : pool DB, queues Celery, versions runtime.
 */
export function HealthDetail() {
  const { data, error, isLoading } = useSWR<HealthDetail>(
    "/admin/health-detail",
    fetcher,
    { refreshInterval: 10_000 },
  );

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <p className="text-sm text-text-secondary">Chargement de la sante systeme...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <p className="text-sm text-red-700">
          Sante systeme indisponible. Verifier que l&apos;API repond.
        </p>
      </div>
    );
  }

  const poolUsage =
    data.db_pool.size && data.db_pool.checked_out !== null && data.db_pool.checked_out !== undefined
      ? Math.round((data.db_pool.checked_out / data.db_pool.size) * 100)
      : 0;

  const totalQueueSize = Object.values(data.celery.queues ?? {}).reduce(
    (sum, n) => sum + n,
    0,
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-blue-600" aria-hidden="true" />
            <h4 className="text-xs font-semibold text-gray-500 uppercase">
              Etat global
            </h4>
          </div>
          <p className={`text-lg font-bold ${data.status === "healthy" ? "text-emerald-700" : "text-amber-700"}`}>
            {data.status === "healthy" ? "Operationnel" : "Degrade"}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            uptime {formatUptime(data.uptime_seconds)} - v{data.version}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Database className="h-4 w-4 text-blue-600" aria-hidden="true" />
            <h4 className="text-xs font-semibold text-gray-500 uppercase">
              Pool DB
            </h4>
          </div>
          <p className="text-lg font-bold tabular-nums">
            {data.db_pool.checked_out ?? "—"} / {data.db_pool.size ?? "—"}
          </p>
          <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                poolUsage > 80
                  ? "bg-red-500"
                  : poolUsage > 50
                  ? "bg-amber-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(poolUsage, 100)}%` }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Inbox className="h-4 w-4 text-blue-600" aria-hidden="true" />
            <h4 className="text-xs font-semibold text-gray-500 uppercase">
              Files Celery
            </h4>
          </div>
          <p className="text-lg font-bold tabular-nums">
            {totalQueueSize} <span className="text-xs font-normal text-gray-500">en file</span>
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {Object.keys(data.celery.queues ?? {}).length} queues actives
          </p>
        </div>

        <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Server className="h-4 w-4 text-blue-600" aria-hidden="true" />
            <h4 className="text-xs font-semibold text-gray-500 uppercase">
              Runtime
            </h4>
          </div>
          <p className="text-sm font-semibold">Python {data.runtime.python}</p>
          <p className="text-xs text-gray-500 mt-1">
            FastAPI {data.runtime.fastapi} - PG {String(data.runtime.postgres).split(" ")[0]}
          </p>
        </div>
      </div>

      {Object.keys(data.celery.queues ?? {}).length > 0 && (
        <details className="rounded-xl border border-border bg-white p-4 shadow-sm">
          <summary className="text-sm font-semibold cursor-pointer">
            Detail files Celery
          </summary>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
            {Object.entries(data.celery.queues ?? {}).map(([name, count]) => (
              <div key={name} className="flex justify-between border-b border-gray-100 pb-1">
                <span className="font-mono text-xs text-gray-600">{name}</span>
                <span className={`font-bold tabular-nums ${count > 50 ? "text-amber-600" : "text-gray-900"}`}>
                  {count}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}

      <p className="text-xs text-gray-400 text-right">
        Auto-refresh 10s
      </p>
    </div>
  );
}
