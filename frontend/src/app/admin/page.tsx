"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { fetchJson } from "@/lib/api";
import {
  RefreshCw,
  Users,
  FileText,
  Package,
  CheckCircle,
  AlertCircle,
  Wifi,
  Heart,
  Database,
  Server,
  HardDrive,
  Activity,
  FolderOpen,
  Euro,
  Plus,
  Pencil,
  Trash2,
  Clock,
  BarChart3,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface AuditLogEntry {
  id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

const ACTION_CONFIG: Record<string, { icon: typeof Plus; color: string; bg: string; label: string }> = {
  create: { icon: Plus, color: "text-emerald-600", bg: "bg-emerald-50", label: "Creation" },
  update: { icon: Pencil, color: "text-blue-600", bg: "bg-blue-50", label: "Modification" },
  delete: { icon: Trash2, color: "text-red-600", bg: "bg-red-50", label: "Suppression" },
};

function formatActivityTime(date: string): string {
  const d = new Date(date);
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

interface SyncStatus {
  configured: boolean;
  authenticated: boolean;
  tenant: string | null;
  base_url: string;
}
interface SyncResult {
  created?: number;
  updated?: number;
  skipped?: number;
  fetched?: number;
  total?: number;
  note?: string;
}
interface HealthData {
  status: string;
  services: Record<string, { status: string; response_ms?: number; error?: string }>;
}
interface MetricsData {
  totals: { users: number; clients: number; dossiers: number; factures: number; paiements: number };
  activity: { actions_last_hour: number; active_users_last_hour: number };
}

const SERVICE_ICONS: Record<string, typeof Database> = { postgres: Database, redis: Server, minio: HardDrive };

interface ActivityChartData {
  date: string;
  create: number;
  update: number;
  delete: number;
}

function buildActivityChart(entries: AuditLogEntry[]): ActivityChartData[] {
  const now = new Date();
  const days: ActivityChartData[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const label = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" }).format(d);
    const dateKey = d.toISOString().slice(0, 10);
    days.push({ date: label, create: 0, update: 0, delete: 0, _key: dateKey } as ActivityChartData & {
      _key: string;
    });
  }
  for (const entry of entries) {
    const entryDate = entry.created_at.slice(0, 10);
    const day = (days as (ActivityChartData & { _key: string })[]).find((d) => d._key === entryDate);
    if (day) {
      if (entry.action === "create") day.create++;
      else if (entry.action === "update") day.update++;
      else if (entry.action === "delete") day.delete++;
    }
  }
  return days;
}

export default function AdminPage() {
  const { data: syncStatus, isLoading: syncLoading } = useSWR<SyncStatus>("/sync/status", {
    onError: () => {
      /* ignore */
    },
  });
  const { data: health, isLoading: healthLoading } = useSWR<HealthData>("/admin/health", {
    onError: () => {
      /* ignore */
    },
  });
  const { data: metrics, isLoading: metricsLoading } = useSWR<MetricsData>("/admin/metrics", {
    onError: () => {
      /* ignore */
    },
  });
  const { data: activity } = useSWR<AuditLogEntry[]>("/audit-logs/recent", {
    refreshInterval: 10000,
    onError: () => {
      /* ignore */
    },
  });

  const loading = syncLoading || healthLoading || metricsLoading;
  const [syncing, setSyncing] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, SyncResult>>({});

  const runSync = async (type: string) => {
    setSyncing(type);
    try {
      const result = await fetchJson<SyncResult>(`/sync/${type}`, { method: "POST" });
      setResults((prev) => ({ ...prev, [type]: result }));
    } catch {
      /* ignore */
    } finally {
      setSyncing(null);
    }
  };

  if (loading)
    return (
      <PageLayout title="Chargement...">
        <LoadingState text="Chargement de l'administration..." />
      </PageLayout>
    );

  return (
    <PageLayout
      title="Administration"
      description="Monitoring, synchronisation et parametres"
      breadcrumb={[{ label: "Admin" }]}
    >
      {/* Sante systeme */}
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

      {/* Metriques */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <KPICard icon={Users} label="Utilisateurs" value={metrics.totals.users} color="info" />
          <KPICard icon={Users} label="Clients" value={metrics.totals.clients} color="primary" />
          <KPICard icon={FolderOpen} label="Dossiers" value={metrics.totals.dossiers} color="primary" />
          <KPICard icon={FileText} label="Factures" value={metrics.totals.factures} color="info" />
          <KPICard icon={Activity} label="Actions (1h)" value={metrics.activity.actions_last_hour} color="success" />
          <KPICard icon={Users} label="Actifs (1h)" value={metrics.activity.active_users_last_hour} color="success" />
        </div>
      )}

      {/* Connexion Cosium */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Wifi className="h-5 w-5" /> Connexion Cosium
        </h3>
        {syncStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KPICard
              icon={syncStatus.configured ? CheckCircle : AlertCircle}
              label="Configuration"
              value={syncStatus.configured ? "Configure" : "Non configure"}
              color={syncStatus.configured ? "success" : "danger"}
            />
            <KPICard
              icon={syncStatus.authenticated ? CheckCircle : AlertCircle}
              label="Authentification"
              value={syncStatus.authenticated ? "Connecte" : "Non connecte"}
              color={syncStatus.authenticated ? "success" : "warning"}
            />
            <KPICard icon={Wifi} label="Tenant" value={syncStatus.tenant || "Non defini"} color="info" />
          </div>
        ) : (
          <p className="text-sm text-text-secondary">Non disponible</p>
        )}
      </div>

      {/* Synchronisation */}
      <h3 className="text-lg font-semibold text-text-primary mb-4">Synchronisation manuelle</h3>
      <p className="text-sm text-text-secondary mb-4">Lecture seule : Cosium vers OptiFlow.</p>
      <div className="space-y-4">
        {[
          { key: "customers", label: "Clients", icon: Users, desc: "Synchroniser les fiches clients" },
          { key: "invoices", label: "Factures", icon: FileText, desc: "Importer les factures" },
          { key: "products", label: "Produits", icon: Package, desc: "Importer le catalogue produits" },
        ].map(({ key, label, icon: Icon, desc }) => (
          <div key={key} className="rounded-xl border border-border bg-bg-card p-5 shadow-sm flex items-center gap-4">
            <div className="rounded-lg bg-blue-50 p-2.5">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold">{label}</h4>
              <p className="text-xs text-text-secondary">{desc}</p>
              {results[key] && (
                <p className="text-xs text-emerald-700 mt-1">
                  {results[key].created !== undefined &&
                    `${results[key].created} cree(s), ${results[key].updated} mis a jour`}
                  {results[key].fetched !== undefined && `${results[key].fetched} element(s) recupere(s)`}
                </p>
              )}
            </div>
            <Button variant="outline" onClick={() => runSync(key)} disabled={syncing !== null}>
              <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing === key ? "animate-spin" : ""}`} />
              {syncing === key ? "Sync..." : "Synchroniser"}
            </Button>
          </div>
        ))}
      </div>

      {/* Activity graph */}
      {activity && activity.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mt-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5" /> Activite des 7 derniers jours
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={buildActivityChart(activity)} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="create" name="Creations" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="update" name="Modifications" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="delete" name="Suppressions" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Activite recente */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mt-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5" /> Activite recente
        </h3>
        {activity && activity.length > 0 ? (
          <div className="space-y-1">
            {activity.map((entry) => {
              const config = ACTION_CONFIG[entry.action] || ACTION_CONFIG.update;
              const Icon = config.icon;
              return (
                <div
                  key={entry.id}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors"
                >
                  <div className={`flex-shrink-0 rounded-full p-1.5 ${config.bg}`}>
                    <Icon className={`h-3.5 w-3.5 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary">
                      <span className={`font-medium ${config.color}`}>{config.label}</span>{" "}
                      <span className="text-text-secondary">{entry.entity_type}</span>{" "}
                      <span className="font-mono text-xs text-text-secondary">#{entry.entity_id}</span>
                    </p>
                  </div>
                  <span className="flex-shrink-0 text-xs text-text-secondary">
                    {formatActivityTime(entry.created_at)}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-text-secondary">Aucune activite recente.</p>
        )}
      </div>
    </PageLayout>
  );
}
