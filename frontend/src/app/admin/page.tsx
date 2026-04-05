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
  Activity,
  FolderOpen,
  Plus,
  Pencil,
  Trash2,
  Clock,
  Key,
  Save,
  Calendar,
} from "lucide-react";
import { ActivityChart } from "./components/ActivityChart";
import { HealthStatus } from "./components/HealthStatus";

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
  tenant_name: string | null;
  base_url: string;
  last_sync_at: string | null;
  first_sync_done: boolean;
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
  const [cookieAccessToken, setCookieAccessToken] = useState("");
  const [cookieDeviceCredential, setCookieDeviceCredential] = useState("");
  const [cookieSaving, setCookieSaving] = useState(false);
  const [cookieMessage, setCookieMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

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

  const saveCosiumCookies = async () => {
    if (!cookieAccessToken.trim() || !cookieDeviceCredential.trim()) {
      setCookieMessage({ type: "error", text: "Les deux champs sont obligatoires." });
      return;
    }
    setCookieSaving(true);
    setCookieMessage(null);
    try {
      const res = await fetchJson<{ status: string; message: string }>("/admin/cosium-cookies", {
        method: "POST",
        body: JSON.stringify({
          access_token: cookieAccessToken.trim(),
          device_credential: cookieDeviceCredential.trim(),
        }),
      });
      setCookieMessage({ type: "success", text: res.message || "Cookies enregistres." });
      setCookieAccessToken("");
      setCookieDeviceCredential("");
    } catch {
      setCookieMessage({ type: "error", text: "Erreur lors de l'enregistrement des cookies." });
    } finally {
      setCookieSaving(false);
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
      <HealthStatus health={health} />

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

      {/* Synchronisation Cosium — Statut detaille */}
      {syncStatus && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5" /> Synchronisation Cosium
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KPICard
              icon={syncStatus.first_sync_done ? CheckCircle : AlertCircle}
              label="Premiere synchronisation"
              value={syncStatus.first_sync_done ? "Effectuee" : "Non effectuee"}
              color={syncStatus.first_sync_done ? "success" : "warning"}
            />
            <KPICard
              icon={Clock}
              label="Derniere synchronisation"
              value={
                syncStatus.last_sync_at
                  ? new Intl.DateTimeFormat("fr-FR", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    }).format(new Date(syncStatus.last_sync_at))
                  : "Jamais"
              }
              color={syncStatus.last_sync_at ? "info" : "warning"}
            />
            <KPICard
              icon={Wifi}
              label="Type ERP"
              value={(syncStatus as SyncStatus & { erp_type?: string }).erp_type || "cosium"}
              color="info"
            />
          </div>
        </div>
      )}

      {/* Acces Cosium — Cookies */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Key className="h-5 w-5" /> Acces Cosium — Cookies navigateur
        </h3>
        <p className="text-sm text-text-secondary mb-4">
          Pour renouveler l&apos;acces, connectez-vous sur Cosium dans votre navigateur, puis copiez les cookies{" "}
          <code className="bg-gray-100 px-1 rounded text-xs">access_token</code> et{" "}
          <code className="bg-gray-100 px-1 rounded text-xs">device-credential</code> depuis les DevTools (onglet
          Application &gt; Cookies).
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm font-medium text-text-primary block mb-1">Cookie access_token</label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Collez le cookie access_token ici..."
              value={cookieAccessToken}
              onChange={(e) => setCookieAccessToken(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-text-primary block mb-1">Cookie device-credential</label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Collez le cookie device-credential ici..."
              value={cookieDeviceCredential}
              onChange={(e) => setCookieDeviceCredential(e.target.value)}
            />
          </div>
        </div>
        {cookieMessage && (
          <p className={`text-sm mb-3 ${cookieMessage.type === "success" ? "text-emerald-600" : "text-red-600"}`}>
            {cookieMessage.text}
          </p>
        )}
        <Button onClick={saveCosiumCookies} disabled={cookieSaving}>
          <Save className="h-4 w-4 mr-1.5" />
          {cookieSaving ? "Enregistrement..." : "Enregistrer les cookies"}
        </Button>
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
      {activity && <ActivityChart activity={activity} />}

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
